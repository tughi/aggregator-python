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
    reader_tags = storm.properties.Int()
    server_tags = storm.properties.Int()

    def __init__(self, feed, poll, guid, data, updated):
        self.feed = feed
        self.poll = poll
        self.guid = guid
        self.updated = updated
        self.data = json.dumps(data)

    def as_dict(self):
        return json.loads(self.data)

    def get_tags(self):
        return self.reader_tags | self.server_tags


Feed.entries = storm.references.ReferenceSet(Feed.id, Entry.feed_id)


class Tag(object):
    __storm_table__ = 'tag'
    id = storm.properties.Int(primary=True)
    name = storm.properties.Chars()
    flag = storm.properties.Int()

    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.flag = 1 << (id - 1)


def open_database():
    database = storm.database.create_database('sqlite:aggregator.db')

    store = storm.store.Store(database)

    DATABASE_VERSION = 3

    version = store.execute('PRAGMA user_version').get_one()[0]

    if version == 0:
        # create schema
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
                poll INTEGER NOT NULL,
                updated INTEGER,
                data TEXT NOT NULL,
                reader_tags INTEGER NOT NULL DEFAULT 0,
                server_tags INTEGER NOT NULL DEFAULT 0,
                UNIQUE (feed_id, guid),
                FOREIGN KEY (feed_id) REFERENCES feed (id)
            )
        ''')
        store.execute('''
            CREATE TABLE tag (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                flag INTEGER UNIQUE NOT NULL
            )
        ''')
        store.add(Tag(1, 'read'))
        store.add(Tag(2, 'star'))
    else:
        # upgrade schema
        if version <= 1:
            store.execute('ALTER TABLE feed ADD COLUMN favicon TEXT')

        if version <= 2:
            store.execute('''
                CREATE TABLE tag (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    flag INTEGER UNIQUE NOT NULL
                )
            ''')
            store.add(Tag(1, 'read'))
            store.add(Tag(2, 'star'))

            # migrate the entry table
            store.execute('ALTER TABLE entry RENAME TO old_entry')
            store.execute('''
                CREATE TABLE entry (
                    id INTEGER PRIMARY KEY,
                    feed_id INTEGER NOT NULL,
                    guid TEXT NOT NULL,
                    poll INTEGER NOT NULL,
                    updated INTEGER,
                    data TEXT NOT NULL,
                    reader_tags INTEGER NOT NULL DEFAULT 0,
                    server_tags INTEGER NOT NULL DEFAULT 0,
                    UNIQUE (feed_id, guid),
                    FOREIGN KEY (feed_id) REFERENCES feed (id)
                )
            ''')
            store.execute('''
                INSERT INTO entry
                    SELECT
                        id, feed_id, guid, poll, updated, data, like('%|read|%', reader_tags) | CASE like('%|star|%', reader_tags) WHEN 1 THEN 2 ELSE 0 END, 0
                    FROM old_entry
            ''')
            store.execute('DROP TABLE old_entry')

    if version != DATABASE_VERSION:
        # update database version
        store.execute('PRAGMA user_version = %d' % DATABASE_VERSION)
        store.commit()

    store.close()

    return database
