from datetime import datetime
from datetime import timezone

import feedparser
import pytest

from aggregator import engine
from aggregator.models import Entry
from aggregator.models import Feed
from aggregator.models import db

FEED_XML = '''<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Fetched Title</title>
    <link>https://example.com/</link>
    <item>
      <title>First post</title>
      <link>https://example.com/first-post</link>
      <guid>https://example.com/first-post</guid>
      <description>Hello</description>
      <pubDate>Mon, 12 Oct 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>'''


@pytest.fixture
def fetch(monkeypatch):
    """Makes every feed fetch end up at `href` (after redirects) with the given HTTP `status`."""

    parse_feed_xml = feedparser.parse

    def fetch(href, status=200):
        def parse(url, **kwargs):
            feed_data = parse_feed_xml(FEED_XML)
            feed_data['href'] = href
            feed_data['status'] = status
            return feed_data

        monkeypatch.setattr(engine.feedparser, 'parse', parse)

    return fetch


def create_feed(url):
    feed = Feed(url=url, title='Original Title')
    db.session.add(feed)
    db.session.flush()
    return feed


def count_entries(feed):
    return Entry.query.filter(Entry.feed_id == feed.id).count()


@pytest.mark.parametrize('url_a, url_b, expected', [
    ('https://example.com/feed', 'https://example.com/rss', True),
    ('http://example.com/feed', 'https://example.com/feed', True),
    ('https://www.example.com/feed', 'https://example.com/feed', True),
    ('https://EXAMPLE.com/feed', 'https://example.com/feed', True),
    ('https://example.com/feed', 'https://spam.example.net/feed', False),
    ('https://blog.example.com/feed', 'https://example.com/feed', False),
])
def test_same_site(url_a, url_b, expected):
    assert engine._same_site(url_a, url_b) is expected


def test_update_feed_ignores_redirect_to_different_site(app, fetch):
    feed = create_feed('https://example.com/feed')
    fetch('https://spam.example.net/feed', status=301)

    engine.update_feed(feed)

    assert feed.url == 'https://example.com/feed'
    assert feed.title == 'Original Title'
    assert count_entries(feed) == 0
    assert 'https://spam.example.net/feed' in feed.last_update_message
    assert feed.next_update_retry == 1
    assert feed.next_update_time > datetime.now(tz=timezone.utc)


def test_update_feed_ignores_temporary_redirect_to_different_site(app, fetch):
    feed = create_feed('https://example.com/feed')
    fetch('https://spam.example.net/feed', status=302)

    engine.update_feed(feed)

    assert feed.url == 'https://example.com/feed'
    assert count_entries(feed) == 0


def test_update_feed_follows_permanent_redirect_on_same_site(app, fetch):
    feed = create_feed('http://www.example.com/feed')
    fetch('https://example.com/feed', status=301)

    engine.update_feed(feed)

    assert feed.url == 'https://example.com/feed'
    assert feed.title == 'Fetched Title'
    assert feed.last_update_message is None
    assert count_entries(feed) == 1


def test_update_feed_without_redirect(app, fetch):
    feed = create_feed('https://example.com/feed')
    fetch('https://example.com/feed')

    engine.update_feed(feed)

    assert feed.url == 'https://example.com/feed'
    assert count_entries(feed) == 1


def test_add_feed_follows_redirect_to_different_site(app, fetch, monkeypatch):
    monkeypatch.setattr(engine, 'update_favicon', lambda feed: None)
    fetch('https://feeds.example.net/feed', status=301)

    result = engine.add_feed('https://example.com/feed')

    assert result['url'] == 'https://feeds.example.net/feed'
    assert result['entries']['created'] == 1
