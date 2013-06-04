from storm.locals import *


class Feed(object):
    __storm_table__ = 'feed'
    id = Int(primary=True)
    url = Chars()
    title = Unicode()
    etag = Chars()
    modified = Chars()

    def __init__(self, url=None, title=None, etag=None, modified=None):
        self.url = url
        self.title = title
        self.etag = etag
        self.modified = modified

class Entry(object):
    __storm_table__ = 'entry'
    id = Int(primary=True)
    feed_id = Int()
    feed = Reference(feed_id, Feed.id)
    url = Chars()
    published = Int()
    updated = Int()
    title = Unicode()
    content = Unicode()
    description = Unicode()

Feed.entries = ReferenceSet(Feed.id, Entry.feed_id)

def open_store():
    database = create_database('sqlite:aggregator.db')

    store = Store(database)

    version = store.execute('PRAGMA user_version').get_one()[0]
    if version == 0:
        store.execute('CREATE TABLE IF NOT EXISTS feed (id INTEGER PRIMARY KEY, url TEXT UNIQUE NOT NULL, title TEXT NOT NULL, etag TEXT, modified TEXT)')
        store.execute('CREATE TABLE IF NOT EXISTS entry (id INTEGER PRIMARY KEY, feed_id INTEGER NOT NULL, url TEXT, published INTEGER, upadted INTEGER, title TEXT, content TEXT, description TEXT)')
        store.execute('PRAGMA user_version = 1')

    store.commit()

    return store
