"""Posts for the similarity tests: two news posted by both feeds, plus unrelated filler posts."""

import json
from datetime import UTC, datetime, timedelta

from aggregator.models import Entry, EntrySimilarity, EntrySimilarityQueue, Feed, db

NOW = datetime.now(tz=UTC).replace(microsecond=0)


def summary(text):
    return json.dumps({"type": "text/html", "language": "en", "value": f"<p>{text}</p>"})


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


def queue(*entry_ids):
    db.session.add_all(EntrySimilarityQueue(entry_id=entry_id) for entry_id in entry_ids)
    db.session.commit()


def queued_entry_ids():
    return {queued.entry_id for queued in EntrySimilarityQueue.query}


# Two news posted by both feeds, plus unrelated filler posts that make the words they share rare
POSTS = [
    (1, 1, "Valve announces the Steam Machine", "Valve reveals a SteamOS console for living rooms", timedelta(hours=5), False),
    (2, 2, "Steam Machine: Valve unveils a SteamOS console", "The Steam Machine runs SteamOS", timedelta(hours=4), False),
    (3, 1, "NASA delays Artemis III", "The Artemis III moon landing slips to 2028", timedelta(hours=3), False),
    (4, 2, "Artemis III moon landing delayed", "NASA moves Artemis III to 2028", timedelta(hours=2), True),
] + [(10 + n, 1 + n % 2, f"Filler post number {n}", f"The unrelated topic {n} with words {n}a and {n}b", timedelta(hours=1), False) for n in range(40)]
