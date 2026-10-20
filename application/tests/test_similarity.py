import json
from datetime import UTC, datetime, timedelta

from posts import NOW, POSTS, add_entries, queue, queued_entry_ids, queued_ready_times, stored_similarities

from aggregator import engine, similarity
from aggregator.models import Entry, EntrySimilarity, EntrySimilarityQueue, Feed, db

SIMILAR_ENTRIES_QUERY = """query ($entryId: Int!) {
   entries(entryIds: [$entryId]) {
      similarEntries { id title }
   }
}"""


def test_entry_text_repeats_the_title_and_strips_html():
    text = similarity.entry_text("Title", json.dumps({"value": "<p>Some &amp; <b>bold</b> text</p>"}))

    assert text.split() == ["Title", "Title", "Some", "&", "bold", "text"]


def test_entry_text_handles_missing_summaries():
    assert similarity.entry_text(None, "null").split() == []
    assert similarity.entry_text("Title", None).split() == ["Title", "Title"]


def test_vectorize_ignores_words_found_in_a_single_document():
    vectors = similarity.vectorize({1: ["shared", "unique"], 2: ["shared", "other"], 3: ["different"]})

    assert vectors == {1: {"shared": 1.0}, 2: {"shared": 1.0}, 3: {}}


def test_update_similarities_stores_matches_in_both_directions(app):
    add_entries(*POSTS)

    similarity.update_similarities([1, 3])

    stored = stored_similarities()
    assert set(stored) == {(1, 2), (2, 1), (3, 4), (4, 3)}
    assert stored[(1, 2)] == stored[(2, 1)]
    assert all(score >= similarity.MIN_SCORE for score in stored.values())


def test_update_similarities_only_compares_entries_published_close_to_each_other(app):
    entries = list(POSTS)
    entries[1] = (*entries[1][:4], similarity.WINDOW + timedelta(days=1), False)
    add_entries(*entries)

    similarity.update_similarities([1])

    assert stored_similarities() == {}


def test_update_similarities_compares_entries_published_far_apart_separately(app, monkeypatch):
    entries = list(POSTS)
    # Publishes the Artemis posts two months earlier than the others
    entries[2] = (*entries[2][:4], timedelta(days=60), False)
    entries[3] = (*entries[3][:4], timedelta(days=60, hours=1), True)
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
    entries = list(POSTS)
    entries.append((5, 1, "Valve announces the Steam Machine price", "Valve prices the SteamOS console", timedelta(hours=1), False))
    add_entries(*entries)

    similarity.update_similarities([1, 2, 5])

    assert len([key for key in stored_similarities() if key[0] == 1]) == 1


def test_delete_feed_deletes_the_similarities_of_its_entries(app):
    add_entries(*POSTS)
    similarity.update_similarities([1, 3])

    engine.delete_feed(2)

    assert stored_similarities() == {}


def test_update_feed_queues_new_entries_instead_of_comparing_them(app, fetch):
    # Published a day before the entry in the fetched feed (see conftest.FEED_XML)
    add_entries((1, 1, "First post", "Hello", NOW - datetime(2026, 10, 11, 10, tzinfo=UTC), False))
    feed = db.session.get_one(Feed, 2)
    fetch("https://b.example/feed")

    engine.update_feed(feed)

    new_entry = db.session.query(Entry).filter(Entry.feed_id == 2).one()
    assert queued_entry_ids() == {new_entry.id}
    assert stored_similarities() == {}


def test_update_feed_does_not_queue_updated_entries(app, fetch):
    add_entries()
    feed = db.session.get_one(Feed, 1)
    fetch("https://a.example/feed")
    engine.update_feed(feed)
    db.session.query(EntrySimilarityQueue).delete()
    db.session.commit()

    engine.update_feed(feed)

    assert queued_entry_ids() == set()


def test_process_queue_finds_the_similar_entries_of_queued_entries(app):
    add_entries(*POSTS)
    queue(1, 3)

    similarity.process_queue()

    assert set(stored_similarities()) == {(1, 2), (2, 1), (3, 4), (4, 3)}
    assert queued_entry_ids() == set()


def test_process_queue_with_an_empty_queue(app):
    add_entries(*POSTS)

    similarity.process_queue()

    assert stored_similarities() == {}


def test_process_queue_processes_entries_published_on_different_days(app):
    entries = list(POSTS)
    # Publishes the Artemis posts two months earlier than the others
    entries[2] = (*entries[2][:4], timedelta(days=60), False)
    entries[3] = (*entries[3][:4], timedelta(days=60, hours=1), True)
    add_entries(*entries)
    queue(1, 3)

    similarity.process_queue()

    assert set(stored_similarities()) == {(1, 2), (2, 1), (3, 4), (4, 3)}
    assert queued_entry_ids() == set()


def test_process_queue_keeps_a_failing_day_queued_and_processes_the_other_days(app, monkeypatch):
    entries = list(POSTS)
    # Publishes the Artemis posts two months earlier than the others
    entries[2] = (*entries[2][:4], timedelta(days=60), False)
    entries[3] = (*entries[3][:4], timedelta(days=60, hours=1), True)
    add_entries(*entries)
    queue(1, 3, 4)
    processed_days = []
    update_similarities = similarity._update_similarities

    def failing_for_the_artemis_day(entry_ids):
        processed_days.append(set(entry_ids))
        if 3 in entry_ids:
            raise RuntimeError("Simulated failure")
        return update_similarities(entry_ids)

    monkeypatch.setattr(similarity, "_update_similarities", failing_for_the_artemis_day)

    similarity.process_queue()

    # The failing day stays queued for the next run, the other day is processed
    assert queued_entry_ids() == {3, 4}
    assert set(stored_similarities()) == {(1, 2), (2, 1)}
    # Each day is tried once per run, not once per queued entry
    assert sorted(processed_days, key=min) == [{1}, {3, 4}]


def test_delete_feed_deletes_the_queued_entries_of_its_entries(app):
    add_entries(*POSTS)
    queue(1, 2)

    engine.delete_feed(2)

    assert queued_entry_ids() == {1}


def test_similar_entries_query_returns_unread_entries_most_similar_first(client):
    add_entries(*POSTS)
    db.session.add_all(
        [
            EntrySimilarity(entry_id=1, similar_entry_id=2, score=0.4),
            EntrySimilarity(entry_id=1, similar_entry_id=3, score=0.8),
            EntrySimilarity(entry_id=1, similar_entry_id=4, score=0.9),
            EntrySimilarity(entry_id=1, similar_entry_id=10, score=0.25),
        ]
    )
    db.session.commit()

    response = client.post("/graphql", json={"query": SIMILAR_ENTRIES_QUERY, "variables": {"entryId": 1}})

    # Entry 4 is read, and entry 10 scores below the default minimum
    similar_entries = [{"id": 3, "title": "NASA delays Artemis III"}, {"id": 2, "title": POSTS[1][2]}]
    assert response.get_json() == {"data": {"entries": [{"similarEntries": similar_entries}]}}


def test_similar_entries_cannot_be_nested(client):
    add_entries(*POSTS)
    query = "{ entries(entryIds: [1]) { similarEntries { similarEntries { id } } } }"

    response = client.post("/graphql", json={"query": query})

    result = response.get_json()
    assert "data" not in result or result["data"] is None
    assert "Cannot query field 'similarEntries' on type 'SimilarEntry'." in result["errors"][0]["message"]


def posts_with_the_artemis_posts_published_earlier():
    entries = list(POSTS)
    entries[2] = (*entries[2][:4], timedelta(days=60), False)
    entries[3] = (*entries[3][:4], timedelta(days=60, hours=1), True)
    return entries


def test_process_queue_delays_a_failing_day(app, monkeypatch):
    add_entries(*posts_with_the_artemis_posts_published_earlier())
    queue(1, 3, 4)
    update_similarities = similarity._update_similarities

    def failing_for_the_artemis_day(entry_ids):
        if 3 in entry_ids:
            raise RuntimeError("Simulated failure")
        return update_similarities(entry_ids)

    monkeypatch.setattr(similarity, "_update_similarities", failing_for_the_artemis_day)
    before = datetime.now(tz=UTC)

    similarity.process_queue()

    after = datetime.now(tz=UTC)
    ready_times = queued_ready_times()
    # The failing day is tried again later; the other day was processed and left the queue
    assert set(ready_times) == {3, 4}
    for ready_time in ready_times.values():
        assert before + timedelta(minutes=15) <= ready_time <= after + timedelta(minutes=15)


def test_process_queue_skips_entries_that_are_not_ready_yet(app):
    add_entries(*posts_with_the_artemis_posts_published_earlier())
    queue(1)
    queue(3, ready_time=datetime.now(tz=UTC) + timedelta(hours=1))

    similarity.process_queue()

    assert queued_entry_ids() == {3}
    assert set(stored_similarities()) == {(1, 2), (2, 1)}


def test_process_queue_processes_delayed_entries_once_they_are_ready(app):
    add_entries(*posts_with_the_artemis_posts_published_earlier())
    queue(3, ready_time=datetime.now(tz=UTC) - timedelta(minutes=1))

    similarity.process_queue()

    assert queued_entry_ids() == set()
    assert set(stored_similarities()) == {(3, 4), (4, 3)}


def test_process_queue_does_not_mix_delayed_entries_into_a_ready_day(app, monkeypatch):
    add_entries(*posts_with_the_artemis_posts_published_earlier())
    # Entries 3 and 4 were published on the same day, but only entry 4 is ready
    queue(3, ready_time=datetime.now(tz=UTC) + timedelta(hours=1))
    queue(4)
    processed_days = []
    update_similarities = similarity._update_similarities

    def recording(entry_ids):
        processed_days.append(set(entry_ids))
        return update_similarities(entry_ids)

    monkeypatch.setattr(similarity, "_update_similarities", recording)

    similarity.process_queue()

    assert processed_days == [{4}]
    assert queued_entry_ids() == {3}
