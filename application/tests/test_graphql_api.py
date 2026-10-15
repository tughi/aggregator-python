"""Records the GraphQL API as the React client (clients/web/src/reader/Session.js) and GraphiQL use it."""

import json
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest

from aggregator import engine
from aggregator.models import Entry
from aggregator.models import Feed
from aggregator.models import db

# Copied from clients/web/src/reader/Session.js
ENTRY_FIELDS = """{
   id
   feedId
   title
   link
   summary { value }
   content { value }
   author { name }
   publishText
   publishTime
   keepTime
   readTime
   starTime
}"""

SESSION_QUERY = (
    """query ($feedId: Int, $onlyUnread: Boolean, $onlyStarred: Boolean, $entriesLimit: Int!, $latestFirst: Boolean, $maxAge: Int) {
   session(feedId: $feedId, onlyUnread: $onlyUnread, onlyStarred: $onlyStarred, latestFirst: $latestFirst, maxAge: $maxAge) {
      entries(limit: $entriesLimit) %s
      entryIds
      feeds {
         id
         faviconUrl
         title
         userTitle
         unreadEntries
      }
      unreadEntries
      starredEntries
   }
}"""
    % ENTRY_FIELDS
)

ENTRIES_QUERY = (
    """query ($entryIds: [Int]!) {
   entries(entryIds: $entryIds) %s
}"""
    % ENTRY_FIELDS
)

UPDATE_ENTRY_STATE_MUTATION = (
    """mutation($entryId: Int!, $keepTime: DateTime, $readTime: DateTime, $starTime: DateTime) {
   result: updateEntryState(id: $entryId, keepTime: $keepTime, readTime: $readTime, starTime: $starTime) {
      entry %s
   }
}"""
    % ENTRY_FIELDS
)

NOW = datetime.now(tz=timezone.utc).replace(microsecond=0)


def iso(time):
    return time.isoformat()


@pytest.fixture
def data(app):
    """Two feeds and four entries, with known timestamps and states."""
    feed_a = Feed(id=1, url="https://a.example/feed", title="Feed A", favicon_url="https://a.example/favicon.ico")
    feed_b = Feed(id=2, url="https://b.example/feed", title="Feed B", user_title="My B")
    db.session.add_all([feed_a, feed_b])

    def entry(id, feed, published, **states):
        return Entry(
            id=id,
            feed_id=feed.id,
            uid=f"entry-{id}",
            link=f"https://example.com/{id}",
            title=f"Entry {id}",
            summary=json.dumps(dict(type="text/html", language="en", value=f"<p>Summary {id}</p>")),
            content=json.dumps([dict(type="text/html", language="en", value=f'<p>Content {id}</p><script>alert({id})</script><a href="/more">more</a>')]),
            author=json.dumps(dict(name=f"Author {id}", href=None, email=None)),
            publish_text=f"published {id}",
            publish_time=published,
            insert_time=published,
            update_time=published,
            **states,
        )

    times = dict(
        e1=NOW - timedelta(hours=3),
        e2=NOW - timedelta(hours=2),
        e3=NOW - timedelta(hours=1),
        e4=NOW - timedelta(days=40),
        read=NOW - timedelta(minutes=30),
        kept=NOW - timedelta(minutes=20),
        starred=NOW - timedelta(minutes=10),
    )
    db.session.add_all(
        [
            entry(1, feed_a, times["e1"]),
            entry(2, feed_a, times["e2"], read_time=times["read"]),
            entry(3, feed_b, times["e3"], keep_time=times["kept"], star_time=times["starred"]),
            entry(4, feed_b, times["e4"]),
        ]
    )
    db.session.commit()
    return times


def graphql(client, query, **variables):
    response = client.post("/graphql", json=dict(query=query, variables=variables))
    assert response.status_code == 200
    result = response.get_json()
    assert "errors" not in result, result["errors"]
    return result["data"]


def expected_entry(id, times, read_time=None, keep_time=None, star_time=None):
    return dict(
        id=id,
        feedId=1 if id <= 2 else 2,
        title=f"Entry {id}",
        link=f"https://example.com/{id}",
        summary=dict(value=f"<div><p>Summary {id}</p></div>"),
        content=[dict(value=f'<div><p>Content {id}</p><a href="https://example.com/more">more</a></div>')],
        author=dict(name=f"Author {id}"),
        publishText=f"published {id}",
        publishTime=iso(times[f"e{id}"]),
        keepTime=keep_time and iso(keep_time),
        readTime=read_time and iso(read_time),
        starTime=star_time and iso(star_time),
    )


# The variables Controller.jsx sends for /reader/all, /reader/starred and /reader/feeds/:id
ALL = dict(feedId=None, onlyUnread=True, onlyStarred=False, entriesLimit=50)
STARRED = dict(feedId=None, onlyUnread=False, onlyStarred=True, entriesLimit=50)


def test_session_for_all_unread_entries(client, data):
    session = graphql(client, SESSION_QUERY, **ALL)["session"]

    assert session == dict(
        entries=[
            expected_entry(4, data),
            expected_entry(1, data),
            expected_entry(3, data, keep_time=data["kept"], star_time=data["starred"]),
        ],
        entryIds=[4, 1, 3],
        feeds=[
            dict(id=1, faviconUrl="https://a.example/favicon.ico", title="Feed A", userTitle=None, unreadEntries=1),
            dict(id=2, faviconUrl=None, title="Feed B", userTitle="My B", unreadEntries=2),
        ],
        unreadEntries=3,
        starredEntries=1,
    )


def test_session_for_starred_entries(client, data):
    session = graphql(client, SESSION_QUERY, **STARRED)["session"]

    assert session["entryIds"] == [3]
    assert [entry["id"] for entry in session["entries"]] == [3]


def test_session_for_one_feed(client, data):
    session = graphql(client, SESSION_QUERY, **dict(ALL, feedId=2))["session"]

    assert session["entryIds"] == [4, 3]
    # The counts stay global, not limited to the selected feed
    assert session["unreadEntries"] == 3
    assert [feed["unreadEntries"] for feed in session["feeds"]] == [1, 2]


def test_session_includes_read_entries_when_not_only_unread(client, data):
    session = graphql(client, SESSION_QUERY, **dict(ALL, onlyUnread=False))["session"]

    assert session["entryIds"] == [4, 1, 2, 3]


def test_session_latest_first(client, data):
    session = graphql(client, SESSION_QUERY, **dict(ALL, latestFirst=True))["session"]

    assert session["entryIds"] == [3, 1, 4]


def test_session_max_age_limits_entries_and_counts(client, data):
    session = graphql(client, SESSION_QUERY, **dict(ALL, maxAge=1))["session"]

    assert session["entryIds"] == [1, 3]
    assert session["unreadEntries"] == 2
    assert session["starredEntries"] == 1
    assert [feed["unreadEntries"] for feed in session["feeds"]] == [1, 1]


def test_session_limits_the_first_page_of_entries(client, data):
    session = graphql(client, SESSION_QUERY, **dict(ALL, entriesLimit=2))["session"]

    assert session["entryIds"] == [4, 1, 3]
    assert [entry["id"] for entry in session["entries"]] == [4, 1]


def test_session_defaults_to_unread_entries(client, data):
    session = graphql(client, "{ session { entryIds } }")["session"]

    assert session["entryIds"] == [4, 1, 3]


def test_entries_by_id_keep_the_requested_order(client, data):
    entries = graphql(client, ENTRIES_QUERY, entryIds=[3, 1, 2])["entries"]

    assert entries == [
        expected_entry(3, data, keep_time=data["kept"], star_time=data["starred"]),
        expected_entry(1, data),
        expected_entry(2, data, read_time=data["read"]),
    ]


def test_entries_by_id_return_null_for_unknown_ids(client, data):
    entries = graphql(client, ENTRIES_QUERY, entryIds=[1, 999])["entries"]

    assert [entry and entry["id"] for entry in entries] == [1, None]


def test_entry_without_summary_content_or_author(client, data):
    entry = db.session.get(Entry, 1)
    entry.summary = json.dumps(None)
    entry.content = json.dumps([])
    entry.author = json.dumps(None)
    db.session.commit()

    entries = graphql(client, ENTRIES_QUERY, entryIds=[1])["entries"]

    assert (entries[0]["summary"], entries[0]["content"], entries[0]["author"]) == (None, [], None)


def test_update_entry_state_marks_read(client, data):
    # Session.js sends Date.toISOString() values, with milliseconds
    read_time = NOW.replace(tzinfo=None).isoformat() + ".000Z"

    result = graphql(client, UPDATE_ENTRY_STATE_MUTATION, entryId=1, keepTime=None, readTime=read_time, starTime=None)["result"]

    assert result["entry"] == expected_entry(1, data, read_time=NOW)
    assert db.session.get(Entry, 1).read_time == NOW


def test_update_entry_state_overwrites_all_three_times(client, data):
    result = graphql(client, UPDATE_ENTRY_STATE_MUTATION, entryId=3, readTime=iso(NOW))["result"]

    # keepTime and starTime weren't passed, so they're cleared
    assert (result["entry"]["keepTime"], result["entry"]["readTime"], result["entry"]["starTime"]) == (None, iso(NOW), None)


def test_update_entry_state_for_unknown_entry(client, data):
    response = client.post("/graphql", json=dict(query=UPDATE_ENTRY_STATE_MUTATION, variables=dict(entryId=999)))

    assert [error["message"] for error in response.get_json()["errors"]] == ["No such entry"]


def test_feeds(client, data):
    feeds = graphql(client, "{ feeds { id url title userTitle link faviconUrl updateMode lastUpdateMessage unreadEntries } }")["feeds"]

    assert sorted(feeds, key=lambda feed: feed["id"]) == [
        dict(
            id=1,
            url="https://a.example/feed",
            title="Feed A",
            userTitle=None,
            link=None,
            faviconUrl="https://a.example/favicon.ico",
            updateMode="AUTO",
            lastUpdateMessage=None,
            unreadEntries=1,
        ),
        dict(
            id=2,
            url="https://b.example/feed",
            title="Feed B",
            userTitle="My B",
            link=None,
            faviconUrl=None,
            updateMode="AUTO",
            lastUpdateMessage=None,
            unreadEntries=2,
        ),
    ]


def test_create_feed(client, app, fetch, no_favicons):
    fetch("https://c.example/feed")

    result = graphql(client, 'mutation { createFeed(url: " https://c.example/feed ", userTitle: "My C") { ok feedId feed { id url title userTitle } } }')

    assert result["createFeed"] == dict(ok=True, feedId=1, feed=dict(id=1, url="https://c.example/feed", title="Fetched Title", userTitle="My C"))


def test_update_feed(client, data):
    result = graphql(client, 'mutation { updateFeed(id: 1, url: "https://a.example/new-feed", userTitle: " New A ") { ok feed { id url userTitle } } }')

    assert result["updateFeed"] == dict(ok=True, feed=dict(id=1, url="https://a.example/new-feed", userTitle="New A"))
    # A changed URL is fetched on the next update
    assert db.session.get(Feed, 1).next_update_time <= datetime.now(tz=timezone.utc)


def test_update_feed_for_unknown_feed(client, data):
    response = client.post("/graphql", json=dict(query='mutation { updateFeed(id: 999, userTitle: "X") { ok } }'))

    assert [error["message"] for error in response.get_json()["errors"]] == ["No such feed"]


def test_refresh_feed(client, data, fetch):
    fetch("https://a.example/feed")

    result = graphql(client, "mutation { refreshFeed(id: 1, forced: true) { feed { id title entriesCreated entriesUpdated } } }")

    assert result["refreshFeed"] == dict(feed=dict(id=1, title="Fetched Title", entriesCreated=1, entriesUpdated=0))


def test_refresh_feed_favicon(client, data, monkeypatch):
    def update_favicon(feed):
        feed.favicon_url = "https://a.example/new-favicon.ico"

    monkeypatch.setattr(engine, "update_favicon", update_favicon)

    result = graphql(client, "mutation { refreshFeedFavicon(id: 1) { feed { id faviconUrl } } }")

    assert result["refreshFeedFavicon"] == dict(feed=dict(id=1, faviconUrl="https://a.example/new-favicon.ico"))


def feed_entry_ids(client, arguments):
    return [entry["id"] for entry in graphql(client, "{ feedEntries(%s) { id } }" % arguments)["feedEntries"]]


def test_feed_entries_newest_first_including_read_entries(client, data):
    assert feed_entry_ids(client, "feedId: 1") == [2, 1]
    assert feed_entry_ids(client, "feedId: 2") == [3, 4]


def test_feed_entries_by_read_state(client, data):
    assert feed_entry_ids(client, "feedId: 1, read: true") == [2]
    assert feed_entry_ids(client, "feedId: 1, read: false") == [1]


def test_feed_entries_paging(client, data):
    assert feed_entry_ids(client, "feedId: 2, limit: 1") == [3]
    assert feed_entry_ids(client, "feedId: 2, limit: 1, offset: 1") == [4]


def test_feed_entries_return_full_entries(client, data):
    entries = graphql(client, "{ feedEntries(feedId: 1, read: true) %s }" % ENTRY_FIELDS)["feedEntries"]

    assert entries == [expected_entry(2, data, read_time=data["read"])]


def test_feed_entries_for_unknown_feed(client, data):
    response = client.post("/graphql", json=dict(query="{ feedEntries(feedId: 999) { id } }"))

    assert [error["message"] for error in response.get_json()["errors"]] == ["No such feed"]


def test_delete_feed_removes_the_feed_and_its_entries(client, data):
    result = graphql(client, "mutation { deleteFeed(id: 1) { ok } }")

    assert result["deleteFeed"] == dict(ok=True)
    assert [feed.id for feed in Feed.query] == [2]
    assert Entry.query.filter(Entry.feed_id == 1).count() == 0
    assert Entry.query.filter(Entry.feed_id == 2).count() == 2


def test_delete_feed_for_unknown_feed(client, data):
    response = client.post("/graphql", json=dict(query="mutation { deleteFeed(id: 999) { ok } }"))

    assert [error["message"] for error in response.get_json()["errors"]] == ["No such feed"]
    assert Feed.query.count() == 2


def test_session_orders_entries_with_the_same_publish_time_by_id(client, data):
    db.session.get(Entry, 4).publish_time = data["e1"]
    db.session.commit()

    assert graphql(client, "{ session { entryIds } }")["session"]["entryIds"] == [1, 4, 3]
    assert graphql(client, "{ session(latestFirst: true) { entryIds } }")["session"]["entryIds"] == [3, 4, 1]
