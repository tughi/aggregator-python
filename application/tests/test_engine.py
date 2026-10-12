from datetime import datetime
from datetime import timezone

import pytest

from aggregator import engine
from aggregator.models import Entry
from aggregator.models import Feed
from aggregator.models import db


def create_feed(url):
    feed = Feed(url=url, title="Original Title")
    db.session.add(feed)
    db.session.flush()
    return feed


def count_entries(feed):
    return Entry.query.filter(Entry.feed_id == feed.id).count()


@pytest.mark.parametrize(
    "url_a, url_b, expected",
    [
        ("https://example.com/feed", "https://example.com/rss", True),
        ("http://example.com/feed", "https://example.com/feed", True),
        ("https://www.example.com/feed", "https://example.com/feed", True),
        ("https://EXAMPLE.com/feed", "https://example.com/feed", True),
        ("https://example.com/feed", "https://spam.example.net/feed", False),
        ("https://blog.example.com/feed", "https://example.com/feed", False),
    ],
)
def test_same_site(url_a, url_b, expected):
    assert engine._same_site(url_a, url_b) is expected


def test_update_feed_ignores_redirect_to_different_site(app, fetch):
    feed = create_feed("https://example.com/feed")
    fetch("https://spam.example.net/feed", status=301)

    engine.update_feed(feed)

    assert feed.url == "https://example.com/feed"
    assert feed.title == "Original Title"
    assert count_entries(feed) == 0
    assert "https://spam.example.net/feed" in feed.last_update_message
    assert feed.next_update_retry == 1
    assert feed.next_update_time > datetime.now(tz=timezone.utc)


def test_update_feed_ignores_temporary_redirect_to_different_site(app, fetch):
    feed = create_feed("https://example.com/feed")
    fetch("https://spam.example.net/feed", status=302)

    engine.update_feed(feed)

    assert feed.url == "https://example.com/feed"
    assert count_entries(feed) == 0


def test_update_feed_follows_permanent_redirect_on_same_site(app, fetch):
    feed = create_feed("http://www.example.com/feed")
    fetch("https://example.com/feed", status=301)

    engine.update_feed(feed)

    assert feed.url == "https://example.com/feed"
    assert feed.title == "Fetched Title"
    assert feed.last_update_message is None
    assert count_entries(feed) == 1


def test_update_feed_without_redirect(app, fetch):
    feed = create_feed("https://example.com/feed")
    fetch("https://example.com/feed")

    engine.update_feed(feed)

    assert feed.url == "https://example.com/feed"
    assert count_entries(feed) == 1


def test_add_feed_follows_redirect_to_different_site(app, fetch, no_favicons):
    fetch("https://feeds.example.net/feed", status=301)

    result = engine.add_feed("https://example.com/feed")

    assert result["url"] == "https://feeds.example.net/feed"
    assert result["entries"]["created"] == 1


RSS_WITH_PUBLISHED_AND_UPDATED_XML = """
<?xml version="1.0"?>
<rss version="2.0" xmlns:dcterms="http://purl.org/dc/terms/">
  <channel>
    <title>Fetched Title</title>
    <item>
      <title>Edited post</title>
      <guid>https://example.com/edited-post</guid>
      <pubDate>Mon, 12 Oct 2026 10:00:00 GMT</pubDate>
      <dcterms:modified>2026-10-14T10:00:00Z</dcterms:modified>
    </item>
  </channel>
</rss>
"""

ATOM_WITH_ONLY_UPDATED_XML = """
<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Fetched Title</title>
  <entry>
    <title>Atom post</title>
    <id>https://example.com/atom-post</id>
    <updated>2026-10-13T10:00:00Z</updated>
  </entry>
</feed>
"""


@pytest.mark.parametrize(
    "xml, expected_publish_time",
    [
        (RSS_WITH_PUBLISHED_AND_UPDATED_XML, datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)),
        (ATOM_WITH_ONLY_UPDATED_XML, datetime(2026, 10, 13, 10, 0, tzinfo=timezone.utc)),
    ],
    ids=["rss-with-published-and-updated", "atom-with-only-updated"],
)
def test_update_feed_prefers_published_over_updated_time(app, fetch, xml, expected_publish_time):
    feed = create_feed("https://example.com/feed")
    fetch("https://example.com/feed", xml=xml)

    engine.update_feed(feed)

    entry = Entry.query.filter(Entry.feed_id == feed.id).one()
    assert entry.publish_time == expected_publish_time


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://example.com/post", "https://example.com/post"),
        ("http://example.com/post", "http://example.com/post"),
        ("HTTPS://example.com/post", "HTTPS://example.com/post"),
        (None, None),
        ("", None),
        ("javascript:alert(1)", None),
        ("JavaScript:alert(1)", None),
        ("java\tscript:alert(1)", None),
        (" javascript:alert(1)", None),
        ("\x01javascript:alert(1)", None),
        ("data:text/html,<script>alert(1)</script>", None),
        ("file:///etc/passwd", None),
        ("/relative/post", None),
    ],
)
def test_web_url(url, expected):
    assert engine._web_url(url) == expected


JAVASCRIPT_LINKS_XML = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Fetched Title</title>
    <link>javascript:alert(1)</link>
    <item>
      <title>Malicious post</title>
      <link>javascript:alert(document.domain)</link>
      <description>Hello</description>
    </item>
  </channel>
</rss>"""


def test_update_feed_drops_links_that_are_not_web_urls(app, fetch):
    feed = create_feed("https://example.com/feed")
    fetch("https://example.com/feed", xml=JAVASCRIPT_LINKS_XML)

    engine.update_feed(feed)

    entry = Entry.query.filter(Entry.feed_id == feed.id).one()
    assert feed.link is None
    assert entry.link is None
    assert entry.uid == "javascript:alert(document.domain)"
