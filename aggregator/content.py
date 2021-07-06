import json
import logging
from datetime import datetime
from datetime import timezone

from aggregator.models import Entry
from aggregator.models import Feed
from aggregator.models import db
from aggregator.models import epoch_datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def restore(file):
    dump = json.load(file)
    dump_version = dump.get('version')

    with db.session.begin():
        Feed.query.delete()

        if dump_version == 1:
            restore_1(dump)


def restore_1(dump):
    def as_datetime(timestamp: int) -> datetime:
        return datetime.fromtimestamp(timestamp).astimezone(timezone.utc)

    for feed in dump.get('feeds'):
        db.session.add(Feed(
            id=feed.get('id'),
            url=feed.get('url'),
            title=feed.get('title'),
            link=feed.get('link'),
            favicon_url=feed.get('favicon'),
            http_etag=feed.get('etag'),
            http_last_modified=feed.get('modified'),
            last_update_time=as_datetime(feed.get('poll', 0)),
            next_update_time=as_datetime(feed.get('next_poll', 0)),
        ))

    for entry in dump.get('entries'):
        entry_data = json.loads(entry.get('data'))
        db.session.add(Entry(
            id=entry.get('id'),
            feed_id=entry.get('feed_id'),
            uid=entry.get('guid'),
            link=entry_data.get('link'),
            title=entry_data.get('title'),
            summary=json.dumps(entry_data.get('summary')),
            content=json.dumps(entry_data.get('content')),
            author=json.dumps(entry_data.get('author')),
            publish_text=entry_data.get('updated') or entry_data.get('published'),
            publish_time=as_datetime(entry.get('updated')),
            insert_time=as_datetime(entry.get('poll')),
            update_time=as_datetime(entry.get('poll')),
            read_time=epoch_datetime() if entry.get('reader_tags') & 1 == 1 else None,
            star_time=epoch_datetime() if entry.get('reader_tags') & 2 == 2 else None,
        ))
