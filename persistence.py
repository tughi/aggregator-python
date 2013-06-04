import storm.properties
import storm.database
import storm.store
import storm.references


class Feed(object):
    __storm_table__ = 'feed'
    id = storm.properties.Int(primary=True)
    url = storm.properties.Chars()
    title = storm.properties.Unicode()
    etag = storm.properties.Chars()
    modified = storm.properties.Chars()

    def __init__(self, url=None, title=None, etag=None, modified=None):
        self.url = url
        self.title = title
        self.etag = etag
        self.modified = modified


class Entry(object):
    __storm_table__ = 'entry'
    id = storm.properties.Int(primary=True)
    feed_id = storm.properties.Int()
    feed = storm.references.Reference(feed_id, Feed.id)
    url = storm.properties.Chars()
    published = storm.properties.Int()
    updated = storm.properties.Int()
    title = storm.properties.Unicode()
    content = storm.properties.Unicode()
    description = storm.properties.Unicode()


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
                modified TEXT
            )
        ''')
        store.execute('''
            CREATE TABLE entry (
                id INTEGER PRIMARY KEY,
                feed_id INTEGER NOT NULL,
                url TEXT,
                published INTEGER,
                upadted INTEGER,
                title TEXT,
                content TEXT,
                description TEXT
            )
        ''')
        store.execute('PRAGMA user_version = 1')

    store.commit()

    return database
