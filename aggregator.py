# coding=utf-8
import time
import json
from collections import OrderedDict
import urlparse

from storm.expr import Update, Like, Not, Select, Count, And, Alias
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

    feed_link = data.feed.get('link')
    feed_favicon = __get_favicon(feed_link or '{0}://{1}'.format(*urlparse.urlparse(url)))

    feed = store.add(Feed(url, title or data.feed.title, feed_link, feed_favicon, data.get('etag'), data.get('modified'), poll))

    for entry_data in data.entries:
        store.add(Entry(feed, poll, *__as_entry_data(entry_data, poll_time)))

    return feed.as_dict()


def __get_favicon(feed_link):
    data = feedparser.parse(feed_link)
    if data:
        for link in data.feed.get('links', []):
            if link.rel == 'shortcut icon':
                return link.href
        for link in data.feed.get('links', []):
            if link.rel == 'icon':
                return link.href
    return '{0}://{1}/favicon.ico'.format(*urlparse.urlparse(feed_link))


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
            feed.poll_status = -1
            continue

        feed_link = data.feed.get('link')
        status = data.get('status', 0)

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

        day_entries, week_entries = store.execute(
            Select((
                Alias(Select(Count(Entry.id), And(Entry.feed == feed, Entry.updated >= poll - 86400))),
                Alias(Select(Count(Entry.id), And(Entry.feed == feed, Entry.updated >= poll - 604800)))
            ))
        ).get_one()

        poll_rate = 75600 / day_entries if day_entries else 259200 / week_entries if week_entries else 345600

        if poll_rate < 1800:
            # schedule new poll in 15 minutes
            feed.poll_type = u'every 15 minutes'
            feed.next_poll = poll + 900
        elif poll_rate < 3600:
            # schedule new poll in 30 minutes
            feed.poll_type = u'every 30 minutes'
            feed.next_poll = poll + 1800
        elif poll_rate < 10800:
            # schedule new poll in 1 hour
            feed.poll_type = u'every hour'
            feed.next_poll = poll + 3600
        elif poll_rate < 21600:
            # schedule new poll in 3 hours
            feed.poll_type = u'every 3 hours'
            feed.next_poll = poll + 10800
        elif poll_rate < 43200:
            # schedule new poll in 6 hours
            feed.poll_type = u'every 6 hours'
            feed.next_poll = poll + 21600
        elif poll_rate < 86400:
            # schedule new poll in 12 hours
            feed.poll_type = u'every 12 hours'
            feed.next_poll = poll + 43200
        elif poll_rate < 172800:
            # schedule new poll in 1 day
            feed.poll_type = u'every day'
            feed.next_poll = poll + 86400
        elif poll_rate < 259200:
            # schedule new poll in 2 day
            feed.poll_type = u'every 2 days'
            feed.next_poll = poll + 172800
        elif poll_rate < 345600:
            # schedule new poll in 3 day
            feed.poll_type = u'every 3 days'
            feed.next_poll = poll + 259200
        else:
            # schedule new poll in 4 days
            feed.poll_type = u'every 4 days'
            feed.next_poll = poll + 345600

        feed.link = __as_unicode(feed_link)
        feed.etag = __as_unicode(data.get('etag'))
        feed.modified = __as_unicode(data.get('modified'))
        feed.poll = poll
        feed.poll_status = status

        store.commit()


def __as_unicode(data):
    return unicode(data) if data else None


def update_favicons(store):
    for feed in store.find(Feed):
        feed.favicon = __as_unicode(__get_favicon(feed.link or '{0}://{1}'.format(*urlparse.urlparse(feed.url))))
        store.commit()


def delete_feed(store, feed_id):
    store.find(Entry, Entry.feed_id == feed_id).remove()
    store.find(Feed, Feed.id == feed_id).remove()
    store.commit()


def import_opml(store, opml_source):
    result = []

    def import_outline(outline):
        try:
            if outline.type == 'rss':
                result.append(add_feed(store, outline.xmlUrl, outline.title))
                store.commit()
                # TODO: handle commit exceptions
        except AttributeError:
            if len(outline):
                for o in outline:
                    import_outline(o)

    outlines = opml.parse(opml_source)

    import_outline(outlines)

    return result


def get_entries(store, include=None, exclude=None):
    result = []

    selection = [Entry.feed_id == Feed.id]

    # TODO
    # if include:
    #     for tag in include:
    #         selection.append(Like(Entry.reader_tags, '%|{0}|%'.format(tag)))
    #
    # if exclude:
    #     for tag in exclude:
    #         selection.append(Not(Like(Entry.reader_tags, '%|{0}|%'.format(tag))))

    for entry, feed_link, feed_favicon in store.find((Entry, Feed.link, Feed.favicon), *selection).order_by(Entry.updated):
        entry_values = entry.as_dict()
        entry_values['id'] = entry.id
        entry_values['timestamp'] = entry.updated
        entry_values['tags'] = entry.get_tags()
        entry_values['feed_link'] = feed_link
        entry_values['feed_favicon'] = feed_favicon

        result.append(entry_values)

    return result


def tag_entry(store, entry_id, tag):
    store.execute('UPDATE entry SET reader_tags = reader_tags | ? WHERE id = ?', (tag, entry_id))
    store.commit()


def untag_entry(store, entry_id, tag):
    store.execute('UPDATE entry SET reader_tags = reader_tags & ~? WHERE id = ?', (tag, entry_id))
    store.commit()
