import logging
import time

from storm.expr import Select, Count
from persistence import Feed, Entry, Content
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

    if DEBUG:
        print('Adding feed: %s' % url)

    # find existing database feed for the provided url
    store_feed = store.find(Feed, url=url).one()

    if store_feed:
        raise AggregatorException('feed %d already exists for this url' % store_feed.id)

    data = feedparser.parse(url)

    if not data:
        raise AggregatorException('failed to load the feed')

    store_feed = store.add(Feed(
        url=url,
        title=title or data.feed.title,
        etag=data.get('etag'),
        modified=data.get('modified')
    ))

    for entry in data.entries:
        store_entry = store.add(Entry(
            guid=entry.id,
            feed=store_feed,
            link=entry.link,
            title=entry.title,
            published=time.mktime(entry.published_parsed) if entry.published_parsed else None,
            updated=time.mktime(entry.updated_parsed) if entry.updated_parsed else None
        ))

        store.flush()

        summary = entry.get('summary_detail')
        if summary:
            store_entry.summary = store.add(Content(
                entry=store_entry,
                type=summary.type,
                language=summary.language,
                value=summary.value,
                index=-1
            ))

        for index, content in enumerate(entry.get('content', [])):
            store.add(Content(
                entry=store_entry,
                type=content.type,
                language=content.language,
                value=content.value,
                index=index
            ))

    return store_feed.as_dict()


def update_feeds(store):
    feeds = store.find(
        (Feed, Count(Entry.id)),
        Feed.id == Entry.feed_id,
        Entry.updated >= time.time() - 7 * 24 * 60 * 60     # entries updated within a week
    ).group_by(Feed.id)
    for feed, entry_count in feeds:
        print('"%s" has %d entries' % (feed.title, entry_count))


def delete_feed(store, feed_id):
    store.find(
        Content,
        Content.id.is_in(Select(Content.id, (Content.entry_id == Entry.id) & (Entry.feed_id == feed_id)))
    ).remove()
    store.find(Entry, feed_id=feed_id).remove()
    store.find(Feed, id=feed_id).remove()


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

    for entry in store.find(Entry).order_by(Entry.published):
        result.append(entry.as_dict())

    return result
