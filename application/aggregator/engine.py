import calendar
import json
import logging
from collections import OrderedDict
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from urllib.parse import urlparse

import feedparser
import opml
import requests

from aggregator.models import Entry
from aggregator.models import Feed
from aggregator.models import db

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def add_feed(feed_url: str, feed_user_title: str = None):
    logger.info(f"Adding feed: {feed_url}")

    feed = Feed(url=feed_url, title="New Feed", user_title=feed_user_title)

    db.session.add(feed)
    db.session.flush()

    result = update_feed(feed)

    update_favicon(feed)

    return result


def delete_feed(feed_id: int):
    feed = Feed.query.get(feed_id)

    logger.info(f"Deleting feed: {feed.url}")

    db.session.query(Entry).filter(Entry.feed_id == feed_id).delete()
    db.session.delete(feed)
    db.session.commit()


def update_feeds():
    status = []
    for feed in Feed.query.filter(Feed.next_update_time <= datetime.now(tz=timezone.utc)):
        status.append(
            update_feed(feed)
        )
    logger.info(f"Updated {len(status)} feed{'s' if len(status) != 1 else ''}")
    return status


def update_feed(feed: Feed, forced: bool = False):
    logger.info(f"Updating feed - {feed.user_title or feed.title} ({feed.url})")

    update_time = datetime.now(tz=timezone.utc)
    feed.last_update_time = update_time

    feed_data = feedparser.parse(
        feed.url,
        etag=None if forced else feed.http_etag,
        modified=None if forced else feed.http_last_modified,
        resolve_relative_uris=False,
        sanitize_html=False,
    )

    if not feed_data:
        logger.warning(f"Failed to parse feed")

        feed.next_update_retry += 1
        db.session.commit()

        return

    feed.title = feed_data.feed.get('title') or feed.title

    feed.link = feed_data.feed.get('link')
    status = feed_data.get('status', 0)

    if status == 301:
        feed.url = feed_data.get('href')

        logger.info(f"Feed moved to: {feed.url}")

    entries_created, entries_updated = _save_entries(feed, feed_data, update_time)

    schedule_next_update(feed, update_time)

    logger.info(f"Next update time: {feed.next_update_time}")

    feed.http_etag = feed_data.get('etag')
    feed.http_last_modified = feed_data.get('modified')

    db.session.commit()

    feed.entries_created = entries_created
    feed.entries_updated = entries_updated

    return dict(
        id=feed.id,
        title=feed.user_title,
        url=feed.url,
        next_update=feed.next_update_time,
        entries=dict(
            created=entries_created,
            updated=entries_updated,
        ),
    )


def _save_entries(feed: Feed, feed_data, update_time: datetime):
    entries_total = len(feed_data.entries)
    entries_created = 0
    entries_updated = 0

    for entry_data in feed_data.entries:
        entry_link = entry_data.get('link')
        entry_uid = entry_data.get('id') or entry_link

        entry = Entry.query.filter(Entry.feed_id == feed.id, Entry.uid == entry_uid).one_or_none()
        if entry is None:
            entry = Entry(feed_id=feed.id, uid=entry_uid, insert_time=update_time, update_time=update_time)
            entries_created += 1
        else:
            entry.update_time = update_time
            entries_updated += 1

        entry.title = entry_data.get('title')
        entry.link = entry_link
        entry.author = json.dumps(entry_data.get('author_detail'))
        entry.summary = json.dumps(_as_content(entry_data.get('summary_detail')))
        entry.content = json.dumps([_as_content(content_data) for content_data in entry_data.get('content', [])])
        entry.publish_text = entry_data.get('published')
        entry.publish_time = _as_datetime(entry_data.get('updated_parsed') or entry_data.get('published_parsed')) or entry.publish_time or update_time

        db.session.add(entry)
        db.session.commit()

    logger.info(f"From {entries_total} entries, {entries_updated} were updated and {entries_created} new were created")

    return entries_created, entries_updated


def _as_content(content_data):
    return OrderedDict([
        ('type', content_data.type),
        ('language', content_data.language),
        ('value', content_data.value),
    ]) if content_data else None


def _as_datetime(parsed_time):
    if parsed_time:
        timestamp = calendar.timegm(parsed_time)
        result = datetime.fromtimestamp(timestamp)
        return result
    return None


def schedule_next_update(feed: Feed, update_time: datetime):
    day_entries = Entry.query.filter(Entry.feed_id == feed.id, Entry.update_time >= update_time - timedelta(days=1)).count()
    week_entries = Entry.query.filter(Entry.feed_id == feed.id, Entry.update_time >= update_time - timedelta(days=7)).count()

    poll_rate = 75600 / day_entries if day_entries else 259200 / week_entries if week_entries else 345600

    if poll_rate < 1800:
        # schedule new poll in 15 minutes
        feed.update_mode = 'EVERY_15_MINUTES'
        feed.next_update_time = update_time + timedelta(minutes=15)
    elif poll_rate < 3600:
        # schedule new poll in 30 minutes
        feed.update_mode = 'EVERY_30_MINUTES'
        feed.next_update_time = update_time + timedelta(minutes=30)
    elif poll_rate < 10800:
        # schedule new poll in 1 hour
        feed.update_mode = 'EVERY_HOUR'
        feed.next_update_time = update_time + timedelta(hours=1)
    elif poll_rate < 21600:
        # schedule new poll in 3 hours
        feed.update_mode = 'EVERY_3_HOURS'
        feed.next_update_time = update_time + timedelta(hours=3)
    else:
        # schedule new poll in 6 hours
        feed.update_mode = 'EVERY_6_HOURS'
        feed.next_update_time = update_time + timedelta(hours=6)

    feed.next_update_time = feed.next_update_time.replace(microsecond=0)


def update_favicons():
    logger.info("Updating favicons")
    for feed in Feed.query.all():
        update_favicon(feed)


def update_favicon(feed: Feed):
    feed_link = feed.link or '{0}://{1}'.format(*urlparse(feed.url))

    logger.info(f"Updating feed favicon - {feed.user_title or feed.title} ({feed_link})")

    feed_favicon_url = None

    data = feedparser.parse(feed_link)
    if data:
        for link in data.feed.get('links', []):
            if link.rel == 'shortcut icon':
                feed_favicon_url = link.href
                break
        if not feed_favicon_url:
            for link in data.feed.get('links', []):
                if link.rel == 'icon':
                    feed_favicon_url = link.href
                    break

    if not feed_favicon_url:
        feed_favicon_url = '{0}://{1}/favicon.ico'.format(*urlparse(feed_link))
        if requests.head(feed_favicon_url).status_code != 200:
            feed_favicon_url = None

    feed.favicon_url = feed_favicon_url or feed.favicon_url
    db.session.commit()

    logger.info(f"Using favicon: {feed.favicon_url}")


def import_opml(opml_source):
    result = []

    def import_outline(outline):
        try:
            if outline.type == 'rss':
                result.append(
                    add_feed(outline.xmlUrl, outline.title)
                )
        except AttributeError:
            if len(outline):
                for o in outline:
                    import_outline(o)

    outlines = opml.parse(opml_source)

    import_outline(outlines)

    return result
