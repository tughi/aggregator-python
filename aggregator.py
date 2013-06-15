import time
import json
from collections import OrderedDict

from storm.expr import Update
from persistence import Feed, Entry
import feedparser
import opml


DEBUG = False


class AggregatorException(BaseException):
    pass


def get_feeds(store):
    result = []

    feeds = store.find(Feed)
    for feed in feeds:
        result.append(feed.as_dict())

    return result


def add_feed(store, url, title):
    if not url:
        raise AggregatorException('The url parameter is required')

    url = unicode(url)
    poll = int(time.time() * 1000)

    if DEBUG:
        print('Adding feed: %s' % url)

    # find existing database feed for the provided url
    feed = store.find(Feed, url=url).one()

    if feed:
        raise AggregatorException('feed %d already exists for this url' % feed.id)

    data = feedparser.parse(url)

    if not data:
        raise AggregatorException('failed to load the feed')

    feed = store.add(Feed(url, title or data.feed.title, data.get('etag'), data.get('modified'), poll))

    for entry_data in data.entries:
        store.add(Entry(feed, poll, __as_entry_data(entry_data)))

    return feed.as_dict()


def __as_entry_data(data):
    return OrderedDict([
        ('id', data.get('id') or data.link),
        ('title', data.title),
        ('link', data.get('link')),
        ('summary', __as_content(data.get('summary_detail'))),
        ('content', [__as_content(content_data) for content_data in data.get('content', [])]),
        ('published', data.get('published')),
        ('updated', data.get('updated')),
        ('timestamp', int(
            time.mktime(data.get('updated_parsed') or data.get('published_parsed') or time.localtime()) * 1000
        ))
    ])


def __as_content(data):
    return OrderedDict([
        ('type', data.type),
        ('language', data.language),
        ('value', data.value),
    ]) if data else None


MINUTE_MILLIS = 60000
HOUR_MILLIS = 60 * MINUTE_MILLIS
DAY_MILLIS = 24 * HOUR_MILLIS
WEEK_MILLIS = 7 * DAY_MILLIS


def update_feeds(store):
    for feed in store.find(Feed, Feed.next_poll <= time.time() * 1000):
        if DEBUG:
            print('Updating feed: %s' % feed.url)

        poll = int(time.time() * 1000)

        data = feedparser.parse(feed.url, etag=feed.etag, modified=feed.modified)

        if not data:
            # TODO: log warning
            continue

        for entry_data in data.entries:
            data = __as_entry_data(entry_data)
            values = {
                'data': json.dumps(data)
            }
            if entry_data.get('updated_parsed') or entry_data.get('published_parsed'):
                values['updated'] = data['timestamp']
            result = store.execute(Update(values, (Entry.feed_id == feed.id) & (Entry.guid == data['id']), Entry))
            if not result.rowcount:
                # not updated since entry doesn't exist
                store.add(Entry(feed, poll, data))

        weekly_entries_count = store.find(Entry, (Entry.feed == feed) & (Entry.updated >= poll - WEEK_MILLIS)).count()
        if weekly_entries_count < 1:
            # schedule new poll in 7 days
            feed.next_poll = poll + WEEK_MILLIS
        elif weekly_entries_count < 5:
            # schedule new poll in 1 day
            feed.next_poll = poll + DAY_MILLIS
        elif weekly_entries_count < 20:
            # schedule new poll in 12 hours
            feed.next_poll = poll + HOUR_MILLIS * 12
        elif weekly_entries_count < 40:
            # schedule new poll in 6 hours
            feed.next_poll = poll + HOUR_MILLIS * 6
        elif weekly_entries_count < 80:
            # schedule new poll in 1 hour
            feed.next_poll = poll + HOUR_MILLIS
        elif weekly_entries_count < 160:
            # schedule new poll in 30 minutes
            feed.next_poll = poll + MINUTE_MILLIS * 30
        else:
            # schedule new poll in 15 minutes
            feed.next_poll = poll + MINUTE_MILLIS * 15

        feed.etag = __as_unicode(data.get('etag'))
        feed.modified = __as_unicode(data.get('modified'))
        feed.poll = poll

        store.commit()


def __as_unicode(data):
    return unicode(data) if data else None


def delete_feed(store, feed_id):
    store.find(Entry, Entry.feed_id == feed_id).remove()
    store.find(Feed, Entry.id == feed_id).remove()


def import_opml(store, opml_source):
    result = []

    def import_outline(outline):
        try:
            if outline.type == 'rss':
                result.append(add_feed(store, outline.xmlUrl, outline.title))
        except AttributeError:
            if len(outline):
                for o in outline:
                    import_outline(o)

    outlines = opml.parse(opml_source)

    import_outline(outlines)

    return result


def get_entries(store):
    result = []

    for entry in store.find(Entry).order_by(Entry.updated):
        entry_values = entry.as_dict()
        entry_values['id'] = entry.id
        result.append(entry_values)

    return result
