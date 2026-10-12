import feedparser
import pytest

from aggregator import engine
from aggregator.app import create_app
from aggregator.models import db

FEED_XML = """
<?xml version="1.0"?>
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
</rss>
"""


class TestConfig(object):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_LOG_LEVEL = None


@pytest.fixture
def app():
    app = create_app(TestConfig())

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def fetch(monkeypatch):
    """Makes every feed fetch return `xml`, ending up at `href` (after redirects) with the given HTTP `status`."""

    parse_feed_xml = feedparser.parse

    def fetch(href, status=200, xml=FEED_XML):
        def parse(url, **kwargs):
            feed_data = parse_feed_xml(xml)
            feed_data["href"] = href
            feed_data["status"] = status
            return feed_data

        monkeypatch.setattr(engine.feedparser, "parse", parse)

    return fetch


@pytest.fixture
def no_favicons(monkeypatch):
    """Skips favicon discovery, which would otherwise make real HTTP requests."""

    monkeypatch.setattr(engine, "update_favicon", lambda feed: None)
