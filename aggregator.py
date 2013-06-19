# coding=utf-8
import time
import json
from collections import OrderedDict

from storm.expr import Update, Like, Not
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
    poll_time = time.localtime()
    poll = time.mktime(poll_time)

    if DEBUG:
        print('Adding feed: %s' % url)

    # find existing database feed for the provided url
    feed = store.find(Feed, url=url).one()

    if feed:
        raise AggregatorException('feed %d already exists for this url' % feed.id)

    data = feedparser.parse(url)

    if not data:
        raise AggregatorException('failed to load the feed')

    feed = store.add(Feed(url, title or data.feed.title, data.feed.get('link'), data.get('etag'), data.get('modified'), poll))

    for entry_data in data.entries:
        store.add(Entry(feed, poll, *__as_entry_data(entry_data, poll_time)))

    return feed.as_dict()


def __as_entry_data(data, poll_time):
    return (
        data.get('id') or data.link,
        OrderedDict([
            ('title', data.title),
            ('link', data.get('link')),
            ('summary', __as_content(data.get('summary_detail'))),
            ('content', [__as_content(content_data) for content_data in data.get('content', [])]),
            ('published', data.get('published')),
            ('updated', data.get('updated'))
        ]),
        time.mktime(data.get('updated_parsed') or data.get('published_parsed') or poll_time)
    )


def __as_content(data):
    return OrderedDict([
        ('type', data.type),
        ('language', data.language),
        ('value', data.value),
    ]) if data else None


def update_feeds(store):
    for feed in store.find(Feed, Feed.next_poll <= time.mktime(time.localtime())):
        if DEBUG:
            print('Updating feed: %s' % feed.url)

        poll_time = time.localtime()
        poll = time.mktime(poll_time)

        data = feedparser.parse(feed.url, etag=feed.etag, modified=feed.modified)

        if not data:
            if DEBUG:
                print('ERROR: Failed to parse feed')
            continue

        feed_link = data.feed.get('link')

        for entry_data in data.entries:
            guid, data, updated = __as_entry_data(entry_data, poll_time)
            values = {
                'data': json.dumps(data)
            }
            if updated != poll:
                values['updated'] = updated
            result = store.execute(Update(values, (Entry.feed_id == feed.id) & (Entry.guid == guid), Entry))
            if not result.rowcount:
                # not updated since entry doesn't exist
                store.add(Entry(feed, poll, guid, data, updated))

        weekly_entries_count = store.find(Entry, (Entry.feed == feed) & (Entry.updated >= poll - 604800)).count()
        if weekly_entries_count < 1:
            # schedule new poll in 7 days
            feed.next_poll = poll + 604800
        elif weekly_entries_count < 5:
            # schedule new poll in 1 day
            feed.next_poll = poll + 86400
        elif weekly_entries_count < 20:
            # schedule new poll in 12 hours
            feed.next_poll = poll + 43200
        elif weekly_entries_count < 40:
            # schedule new poll in 6 hours
            feed.next_poll = poll + 21600
        elif weekly_entries_count < 80:
            # schedule new poll in 1 hour
            feed.next_poll = poll + 3600
        elif weekly_entries_count < 160:
            # schedule new poll in 30 minutes
            feed.next_poll = poll + 1800
        else:
            # schedule new poll in 15 minutes
            feed.next_poll = poll + 900

        feed.link = unicode(feed_link) if feed_link else None
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


def get_entries(store, entry_tags=None):
    result = []

    for entry, feed_link in store.find((Entry, Feed.link), Not(Like(Entry.reader_tags, '%|read|%')), Entry.feed_id == Feed.id).order_by(Entry.updated):
        entry_values = entry.as_dict()
        entry_values['id'] = entry.id
        entry_values['timestamp'] = entry.updated
        entry_values['tags'] = entry.get_tags()
        entry_values['feed_link'] = feed_link

        result.append(entry_values)

    return result


def tag_entry(store, entry_id, tag):
    store.execute('UPDATE entry SET reader_tags = reader_tags || ? || \'|\' WHERE id = ? AND reader_tags NOT LIKE \'%|\' || ? || \'|%\'', (tag, entry_id, tag))
    store.commit()


def untag_entry(store, entry_id, tag):
    store.execute('UPDATE entry SET reader_tags = replace(reader_tags, \'|\' || ? || \'|\', \'|\') WHERE id = ?',
                  (tag, entry_id))
    store.commit()
