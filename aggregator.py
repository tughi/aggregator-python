import time
import json

from storm.expr import Update
from persistence import Feed, Entry
import feedparser
import opml
from collections import OrderedDict


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
        ('link', data.link),
        ('summary', __as_content(data.get('summary_detail'))),
        ('content', [__as_content(content_data) for content_data in data.get('content', [])]),
        ('published', data.get('published')),
        ('updated', data.get('updated')),
        ('timestamp', int(
            time.mktime(data.get('updated_parsed') or data.get('published_parsed') or time.gmtime()) * 1000
        ))
    ])


def __as_content(data):
    return OrderedDict([
        ('type', data.type),
        ('language', data.language),
        ('value', data.value),
    ]) if data else None


def update_feeds(store):
    for feed in store.find(Feed):
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
                'data': json.dumps(data),
                'updated': data['timestamp']
            }
            result = store.execute(Update(values, (Entry.feed_id == feed.id) & (Entry.guid == data['id']), Entry))
            if not result.rowcount:
                # not updated since entry doesn't exist
                store.add(Entry(feed, poll, data))

        feed.etag = data.get('etag')
        feed.modified = data.get('modified')
        feed.poll = poll


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
        result.append(entry.as_dict())

    return result
