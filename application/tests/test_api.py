from pathlib import Path

import pytest

from aggregator import engine
from aggregator.models import Entry
from aggregator.models import Feed

SUBSCRIPTIONS_OPML = Path(__file__).parent.parent / "subscriptions.xml"


@pytest.fixture(autouse=True)
def offline(fetch, no_favicons):
    fetch("https://example.com/feed")


def add_feed(client, url, title=None):
    data = dict(url=url)
    if title:
        data["title"] = title
    response = client.post("/api/feeds", data=data)
    assert response.status_code == 200
    return response.get_json()


def test_get_feeds_when_empty(client):
    response = client.get("/api/feeds")

    assert response.status_code == 200
    assert response.get_json() == []


def test_add_feed(client):
    result = add_feed(client, "https://example.com/feed")

    assert result["url"] == "https://example.com/feed"
    assert result["title"] == "Fetched Title"
    assert result["entries"] == dict(created=1, updated=0)


def test_add_feed_requires_url(client):
    response = client.post("/api/feeds", data={})

    assert response.status_code == 400
    assert response.get_json() == dict(error="The url parameter is required.")


def test_get_feeds_prefers_user_title(client):
    add_feed(client, "https://example.com/feed", title="My Title")
    add_feed(client, "https://example.com/other-feed")

    feeds = client.get("/api/feeds").get_json()

    assert [(feed["url"], feed["title"]) for feed in feeds] == [
        ("https://example.com/feed", "My Title"),
        ("https://example.com/other-feed", "Fetched Title"),
    ]


def test_delete_feed_removes_its_entries(client):
    feed_id = add_feed(client, "https://example.com/feed")["id"]
    assert Entry.query.filter(Entry.feed_id == feed_id).count() == 1

    response = client.delete(f"/api/feeds/{feed_id}")

    assert response.status_code == 200
    assert client.get("/api/feeds").get_json() == []
    assert Entry.query.filter(Entry.feed_id == feed_id).count() == 0


def test_update_feeds_skips_feeds_that_are_not_due(client):
    add_feed(client, "https://example.com/feed")

    response = client.get("/api/update/feeds")

    assert response.status_code == 200
    assert response.get_json() == []


def test_import_opml(app):
    results = engine.import_opml(str(SUBSCRIPTIONS_OPML))

    # 43 RSS outlines, some nested in folders (one more is commented out)
    assert len(results) == 43
    assert Feed.query.count() == 43
    assert Feed.query.filter(Feed.url == "http://xkcd.com/atom.xml").one().user_title == "xkcd.com"
    assert Feed.query.filter(Feed.url == "http://www.autoblog.com/category/paris-motor-show/rss.xml").one().user_title == "paris motor show"


def test_add_feed_rejects_urls_that_are_not_web_urls(client):
    response = client.post("/api/feeds", data=dict(url="file:///etc/passwd"))

    assert response.status_code == 400
    assert response.get_json() == dict(error=engine.NOT_A_WEB_URL_MESSAGE)
    assert Feed.query.count() == 0
