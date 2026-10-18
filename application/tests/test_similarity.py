import json
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from aggregator import engine
from aggregator import similarity
from aggregator.models import Entry
from aggregator.models import EntrySimilarity
from aggregator.models import Feed
from aggregator.models import db

NOW = datetime.now(tz=timezone.utc).replace(microsecond=0)

SIMILAR_ENTRIES_QUERY = """query ($entryId: Int!) {
   entries(entryIds: [$entryId]) {
      similarEntries { id title }
   }
}"""


def summary(text):
    return json.dumps(dict(type="text/html", language="en", value=f"<p>{text}</p>"))


def add_entries(*entries):
    """Adds two feeds and the given (id, feed_id, title, summary text, age, read) entries."""
    db.session.add_all([Feed(id=1, url="https://a.example/feed", title="Feed A"), Feed(id=2, url="https://b.example/feed", title="Feed B")])
    for id, feed_id, title, text, age, read in entries:
        published = NOW - age
        db.session.add(
            Entry(
                id=id,
                feed_id=feed_id,
                uid=f"entry-{id}",
                title=title,
                summary=summary(text),
                content="[]",
                author="null",
                publish_time=published,
                insert_time=published,
                update_time=published,
                read_time=NOW if read else None,
            )
        )
    db.session.commit()


def stored_similarities():
    return {(similarity.entry_id, similarity.similar_entry_id): round(similarity.score, 3) for similarity in EntrySimilarity.query}


# Two stories covered by both feeds, plus unrelated filler that makes the shared story words rare
STORY_ENTRIES = [
    (1, 1, "Valve announces the Steam Machine", "Valve reveals a SteamOS console for living rooms", timedelta(hours=5), False),
    (2, 2, "Steam Machine: Valve unveils a SteamOS console", "The Steam Machine runs SteamOS", timedelta(hours=4), False),
    (3, 1, "NASA delays Artemis III", "The Artemis III moon landing slips to 2028", timedelta(hours=3), False),
    (4, 2, "Artemis III moon landing delayed", "NASA moves Artemis III to 2028", timedelta(hours=2), True),
] + [(10 + n, 1 + n % 2, f"Filler story number {n}", f"The unrelated topic {n} with words {n}a and {n}b", timedelta(hours=1), False) for n in range(40)]


def test_entry_text_repeats_the_title_and_strips_html():
    text = similarity.entry_text("Title", json.dumps(dict(value="<p>Some &amp; <b>bold</b> text</p>")))

    assert text.split() == ["Title", "Title", "Some", "&", "bold", "text"]


def test_entry_text_handles_missing_summaries():
    assert similarity.entry_text(None, "null").split() == []
    assert similarity.entry_text("Title", None).split() == ["Title", "Title"]


def test_vectorize_ignores_words_found_in_a_single_document():
    vectors = similarity.vectorize({1: ["shared", "unique"], 2: ["shared", "other"], 3: ["different"]})

    assert vectors == {1: {"shared": 1.0}, 2: {"shared": 1.0}, 3: {}}


def test_update_similarities_stores_matches_in_both_directions(app):
    add_entries(*STORY_ENTRIES)

    similarity.update_similarities([1, 3])

    stored = stored_similarities()
    assert set(stored) == {(1, 2), (2, 1), (3, 4), (4, 3)}
    assert stored[(1, 2)] == stored[(2, 1)]
    assert all(score >= similarity.MIN_SCORE for score in stored.values())


def test_update_similarities_only_compares_entries_published_close_to_each_other(app):
    entries = list(STORY_ENTRIES)
    entries[1] = entries[1][:4] + (similarity.WINDOW + timedelta(days=1), False)
    add_entries(*entries)

    similarity.update_similarities([1])

    assert stored_similarities() == {}


def test_update_similarities_compares_entries_published_far_apart_separately(app, monkeypatch):
    entries = list(STORY_ENTRIES)
    # Publishes the Artemis story two months earlier than the others
    entries[2] = entries[2][:4] + (timedelta(days=60), False)
    entries[3] = entries[3][:4] + (timedelta(days=60, hours=1), True)
    add_entries(*entries)
    pools = []
    vectorize = similarity.vectorize
    monkeypatch.setattr(similarity, "vectorize", lambda documents: pools.append(set(documents)) or vectorize(documents))

    similarity.update_similarities([1, 3])

    assert set(stored_similarities()) == {(1, 2), (2, 1), (3, 4), (4, 3)}
    # One pool per publish day, neither including the entries published two months apart
    assert sorted(pools, key=len) == [{3, 4}, set(range(1, 3)) | set(range(10, 50))]


def test_update_similarities_keeps_the_best_matches(app, monkeypatch):
    monkeypatch.setattr(similarity, "MAX_SIMILAR_ENTRIES", 1)
    entries = list(STORY_ENTRIES)
    entries.append((5, 1, "Valve announces the Steam Machine price", "Valve prices the SteamOS console", timedelta(hours=1), False))
    add_entries(*entries)

    similarity.update_similarities([1, 2, 5])

    assert len([key for key in stored_similarities() if key[0] == 1]) == 1


def test_delete_feed_deletes_the_similarities_of_its_entries(app):
    add_entries(*STORY_ENTRIES)
    similarity.update_similarities([1, 3])

    engine.delete_feed(2)

    assert stored_similarities() == {}


def test_update_feed_finds_the_similar_entries_of_new_entries(app, fetch):
    # Published a day before the entry in the fetched feed (see conftest.FEED_XML)
    add_entries((1, 1, "First post", "Hello", NOW - datetime(2026, 10, 11, 10, tzinfo=timezone.utc), False))
    feed = db.session.get(Feed, 2)
    fetch("https://b.example/feed")

    engine.update_feed(feed)

    new_entry = Entry.query.filter(Entry.feed_id == 2).one()
    assert set(stored_similarities()) == {(1, new_entry.id), (new_entry.id, 1)}


def test_similar_entries_query_returns_unread_entries_most_similar_first(client):
    add_entries(*STORY_ENTRIES)
    db.session.add_all(
        [
            EntrySimilarity(entry_id=1, similar_entry_id=2, score=0.4),
            EntrySimilarity(entry_id=1, similar_entry_id=3, score=0.8),
            EntrySimilarity(entry_id=1, similar_entry_id=4, score=0.9),
            EntrySimilarity(entry_id=1, similar_entry_id=10, score=0.25),
        ]
    )
    db.session.commit()

    response = client.post("/graphql", json=dict(query=SIMILAR_ENTRIES_QUERY, variables=dict(entryId=1)))

    # Entry 4 is read, and entry 10 scores below the default minimum
    similar_entries = [dict(id=3, title="NASA delays Artemis III"), dict(id=2, title=STORY_ENTRIES[1][2])]
    assert response.get_json() == dict(data=dict(entries=[dict(similarEntries=similar_entries)]))


def test_similar_entries_cannot_be_nested(client):
    add_entries(*STORY_ENTRIES)
    query = "{ entries(entryIds: [1]) { similarEntries { similarEntries { id } } } }"

    response = client.post("/graphql", json=dict(query=query))

    result = response.get_json()
    assert "data" not in result or result["data"] is None
    assert "Cannot query field 'similarEntries' on type 'SimilarEntry'." in result["errors"][0]["message"]
