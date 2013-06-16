import storm.properties
import storm.database
import storm.store
import storm.references
import json


class Feed(object):
    __storm_table__ = 'feed'
    id = storm.properties.Int(primary=True)
    url = storm.properties.Unicode()
    title = storm.properties.Unicode()
    etag = storm.properties.Unicode()
    modified = storm.properties.Unicode()
    poll = storm.properties.Int()
    next_poll = storm.properties.Int()

    def __init__(self, url, title, etag, modified, poll):
        self.url = url
        self.title = unicode(title) if title else None
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

    def __init__(self, feed, poll, guid, data, updated):
        self.feed = feed
        self.poll = poll
        self.guid = guid
        self.updated = updated
        self.data = json.dumps(data)

    def as_dict(self):
        return json.loads(self.data)


Feed.entries = storm.references.ReferenceSet(Feed.id, Entry.feed_id)


def open_database():
    database = storm.database.create_database('sqlite:aggregator.db')

    store = storm.store.Store(database)

    version = store.execute('PRAGMA user_version').get_one()[0]
    if version == 0:
        store.execute('''
            CREATE TABLE feed (
                id INTEGER PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                etag TEXT,
                modified TEXT,
                poll INTEGER NOT NULL,
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
                UNIQUE (feed_id, guid)
                FOREIGN KEY (feed_id) REFERENCES feed (id)
            )
        ''')
        store.execute('PRAGMA user_version = 1')

    store.commit()

    return database
