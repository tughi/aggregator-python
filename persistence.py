# coding=utf-8
import json

import storm.properties
import storm.database
import storm.store
import storm.references


class Feed(object):
    __storm_table__ = 'feed'
    id = storm.properties.Int(primary=True)
    url = storm.properties.Unicode()
    title = storm.properties.Unicode()
    link = storm.properties.Unicode()
    favicon = storm.properties.Unicode()
    etag = storm.properties.Unicode()
    modified = storm.properties.Unicode()
    poll = storm.properties.Int()
    poll_status = storm.properties.Int()
    poll_type = storm.properties.Unicode()
    next_poll = storm.properties.Int()

    def __init__(self, url, title, link, favicon, etag, modified, poll):
        self.url = url
        self.title = unicode(title) if title else None
        self.link = unicode(link) if link else None
        self.favicon = unicode(favicon) if favicon else None
        self.etag = unicode(etag) if etag else None
        self.modified = unicode(modified) if modified else None
        self.poll = poll

    def as_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url
        }


class Entry(object):
    __storm_table__ = 'entry'
    id = storm.properties.Int(primary=True)
    feed_id = storm.properties.Int()
    feed = storm.references.Reference(feed_id, Feed.id)
    guid = storm.properties.Unicode()
    poll = storm.properties.Int()
    updated = storm.properties.Int()
    data = storm.properties.Chars()
    reader_tags = storm.properties.Unicode()
    server_tags = storm.properties.Unicode()

    def __init__(self, feed, poll, guid, data, updated):
        self.feed = feed
        self.poll = poll
        self.guid = guid
        self.updated = updated
        self.data = json.dumps(data)

    def as_dict(self):
        return json.loads(self.data)

    def get_tags(self):
        tags = set()

        reader_tags = self.reader_tags.strip('|')
        if reader_tags:
            tags.update(reader_tags.split('|'))

        server_tags = self.server_tags.strip('|')
        if server_tags:
            tags.update(server_tags.split('|'))

        return list(tags)

Feed.entries = storm.references.ReferenceSet(Feed.id, Entry.feed_id)


def open_database():
    database = storm.database.create_database('sqlite:aggregator.db')

    store = storm.store.Store(database)
    dirty = False

    version = store.execute('PRAGMA user_version').get_one()[0]
    if version < 1:
        store.execute('''
            CREATE TABLE feed (
                id INTEGER PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                link TEXT,
                favicon TEXT,
                etag TEXT,
                modified TEXT,
                poll INTEGER NOT NULL,
                poll_status INTEGER,
                poll_type TEXT,
                next_poll INTEGER NOT NULL DEFAULT 0
            )
        ''')
        store.execute('''
            CREATE TABLE entry (
                id INTEGER PRIMARY KEY,
                feed_id INTEGER NOT NULL,
                guid TEXT NOT NULL,
                poll INT NOT NULL,
                updated INTEGER,
                data TEXT NOT NULL,
                reader_tags TEXT NOT NULL DEFAULT '|',
                server_tags TEXT NOT NULL DEFAULT '|',
                UNIQUE (feed_id, guid)
                FOREIGN KEY (feed_id) REFERENCES feed (id)
            )
        ''')
        store.execute('PRAGMA user_version = 1')
        dirty = True

    if version < 2:
        store.execute('ALTER TABLE feed ADD COLUMN favicon TEXT')
        store.execute('PRAGMA user_version = 2')
        dirty = True

    if dirty:
        store.commit()

    store.close()

    return database
