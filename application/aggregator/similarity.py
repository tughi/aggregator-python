"""Finds entries that cover the same story.

Entries are compared by the TF-IDF cosine similarity of their titles and summaries: words that are frequent in an entry
but rare across the other entries (names, products) weigh the most. Each new entry is scored against the entries
published within `WINDOW` of it, and the best matches are stored in `entry_similarities`, in both directions.
"""

import html
import json
import logging
import math
import re
from collections import Counter, defaultdict
from datetime import timedelta

from aggregator.models import Entry, EntrySimilarity, EntrySimilarityQueue, db

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Only entries published this close to each other are compared
WINDOW = timedelta(days=14)
# Pairs that score lower are not stored
MIN_SCORE = 0.2
# The best matches kept per entry
MAX_SIMILAR_ENTRIES = 10
# Words that appear in more than this share of the compared entries are ignored, like stop words
MAX_DOCUMENT_SHARE = 0.05
# Summaries are cut to this many characters
MAX_SUMMARY_LENGTH = 1500

TAG = re.compile(r"<[^>]+>")
WORD = re.compile(r"\w[\w.\-]*\w")


def entry_text(title: str | None, summary: str | None) -> str:
    """
    Returns the text an entry is compared by: its title, counted twice, followed by its summary as plain text.
    """

    try:
        summary = json.loads(summary) if summary else None
    except ValueError:
        summary = None
    summary_html = summary.get("value") if isinstance(summary, dict) else None
    summary_text = html.unescape(TAG.sub(" ", summary_html or ""))[:MAX_SUMMARY_LENGTH]
    title = title or ""
    return f"{title} {title} {summary_text}"


def tokenize(text: str) -> list[str]:
    return WORD.findall(text.lower())


def vectorize(documents: dict[int, list[str]]) -> dict[int, dict[str, float]]:
    """
    Turns each document's tokens into a unit-length vector of TF-IDF weights.

    Words found in a single document can't match anything, and words found in too many documents carry no meaning, so
    both are left out.
    """

    document_frequency = Counter()
    for tokens in documents.values():
        document_frequency.update(set(tokens))

    documents_count = len(documents)
    max_document_frequency = max(MAX_DOCUMENT_SHARE * documents_count, 2)
    idf = {
        word: math.log((1 + documents_count) / (1 + frequency)) + 1
        for word, frequency in document_frequency.items()
        if 2 <= frequency <= max_document_frequency
    }

    vectors = {}
    for document_id, tokens in documents.items():
        weights = {word: (1 + math.log(count)) * idf[word] for word, count in Counter(tokens).items() if word in idf}
        norm = math.sqrt(sum(weight * weight for weight in weights.values()))
        vectors[document_id] = {word: weight / norm for word, weight in weights.items()} if norm else {}
    return vectors


def score_documents(vectors: dict[int, dict[str, float]], document_ids) -> dict[int, dict[int, float]]:
    """
    Scores each of `document_ids` against all the other vectors, returning only the pairs that share words.
    """

    index = defaultdict(list)
    for document_id, vector in vectors.items():
        for word, weight in vector.items():
            index[word].append((document_id, weight))

    scores = {}
    for document_id in document_ids:
        document_scores = defaultdict(float)
        for word, weight in vectors[document_id].items():
            for other_id, other_weight in index[word]:
                if other_id != document_id:
                    document_scores[other_id] += weight * other_weight
        scores[document_id] = document_scores
    return scores


def update_similarities(entry_ids: list[int]):
    """
    Finds the entries similar to `entry_ids` and stores the matches.

    The entries are processed in groups published on the same day, so the entries they are compared with span at most a
    day plus `WINDOW` on both sides, however far apart the given entries were published.
    """

    if not entry_ids:
        return
    entry_ids_set = set(entry_ids)

    entry_ids_by_day = defaultdict(set)
    for entry_id, publish_time in db.session.query(Entry.id, Entry.publish_time).filter(Entry.id.in_(entry_ids_set)).all():
        entry_ids_by_day[publish_time.date()].add(entry_id)

    matched_entries = sum(_update_similarities(day_entry_ids) for day_entry_ids in entry_ids_by_day.values())

    logger.info(f"Found similar entries for {matched_entries} of {len(entry_ids_set)} entries")


def _update_similarities(entry_ids: set[int]) -> int:
    """
    Finds the entries similar to `entry_ids`, which were published close to each other, and stores the matches.

    Returns how many of `entry_ids` got matches.
    """

    publish_times = [publish_time for (publish_time,) in db.session.query(Entry.publish_time).filter(Entry.id.in_(entry_ids))]
    # Loads only the columns that are needed, since the content of an entry can be large
    rows = (
        db.session.query(Entry.id, Entry.publish_time, Entry.title, Entry.summary)
        .filter(Entry.publish_time >= min(publish_times) - WINDOW, Entry.publish_time <= max(publish_times) + WINDOW)
        .all()
    )
    publish_time_by_id = {entry_id: publish_time for entry_id, publish_time, _, _ in rows}
    vectors = vectorize({entry_id: tokenize(entry_text(title, summary)) for entry_id, _, title, summary in rows})

    matches = defaultdict(dict)
    entry_ids = entry_ids & vectors.keys()
    for entry_id, scores in score_documents(vectors, entry_ids).items():
        for other_id, score in scores.items():
            if score >= MIN_SCORE and abs(publish_time_by_id[entry_id] - publish_time_by_id[other_id]) <= WINDOW:
                matches[entry_id][other_id] = score
                matches[other_id][entry_id] = score

    _save_matches(matches)

    return sum(1 for entry_id in entry_ids if matches.get(entry_id))


def _save_matches(matches: dict[int, dict[int, float]]):
    """
    Merges `matches` into the stored similarities, keeping the best `MAX_SIMILAR_ENTRIES` per entry.
    """

    if not matches:
        return

    stored = EntrySimilarity.query.filter(EntrySimilarity.entry_id.in_(matches.keys())).all()
    for similarity in stored:
        matches[similarity.entry_id].setdefault(similarity.similar_entry_id, similarity.score)
        db.session.delete(similarity)
    db.session.flush()

    for entry_id, scores in matches.items():
        best = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:MAX_SIMILAR_ENTRIES]
        db.session.add_all(EntrySimilarity(entry_id=entry_id, similar_entry_id=similar_entry_id, score=score) for similar_entry_id, score in best)
    db.session.commit()


def process_queue() -> None:
    """
    Processes the queued entries one publish day at a time.
    """

    logger.info("Starting to process queued entries")

    seen_entry_ids = set()

    while True:
        queued_entry = (
            db.session.query(EntrySimilarityQueue.entry_id, Entry.publish_time)
            .filter(EntrySimilarityQueue.entry_id.not_in(seen_entry_ids), EntrySimilarityQueue.entry_id == Entry.id)
            .first()
        )
        if not queued_entry:
            logger.info(f"Finished processing {len(seen_entry_ids)} queued entries")
            return  # empty queue

        # Load all entries from the same day
        day = queued_entry[1].replace(hour=0, minute=0, second=0, microsecond=0)
        entry_ids = {
            entry_id
            for (entry_id,) in db.session.query(EntrySimilarityQueue.entry_id)
            .join(Entry, EntrySimilarityQueue.entry_id == Entry.id)
            .filter(
                Entry.publish_time >= day,
                Entry.publish_time < day + timedelta(days=1),
            )
        }

        # Mark all day entries from queue as seen
        seen_entry_ids.update(entry_ids)

        # Process similarity for the day entries
        try:
            _update_similarities(entry_ids)
        except Exception:
            logger.exception("Failed to update the similar entries")
            db.session.rollback()
            continue

        # Remove processed entries from queue
        db.session.query(EntrySimilarityQueue).filter(EntrySimilarityQueue.entry_id.in_(entry_ids)).delete(synchronize_session=False)

        # Persist changes
        db.session.commit()
