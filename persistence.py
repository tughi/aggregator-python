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
        self.etag = str(etag) if etag else None
        self.modified = str(modified) if modified else None

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
    guid = storm.properties.Chars()
    link = storm.properties.Chars()
    title = storm.properties.Unicode()
    summary_id = storm.properties.Int()
    published = storm.properties.Int()
    updated = storm.properties.Int()

    def __init__(self, guid=None, feed=None, link=None, title=None, published=None, updated=None):
        self.guid = str(guid) if guid else None
        self.feed = feed
        self.link = str(link) if link else None
        self.title = title
        self.published = published
        self.updated = updated

    def as_dict(self):
        return {
            'id': self.guid,
            'title': self.title,
            'link': self.link,
            'summary': self.summary.as_dict() if self.summary else None,
            'content': [content.as_dict() for content in self.content.find(Content.index >= 0)]
        }


Feed.entries = storm.references.ReferenceSet(Feed.id, Entry.feed_id)


class Content(object):
    __storm_table__ = 'content'
    id = storm.properties.Int(primary=True)
    entry_id = storm.properties.Int()
    entry = storm.references.Reference(entry_id, Entry.id)
    type = storm.properties.Chars()
    language = storm.properties.Chars()
    value = storm.properties.Unicode()
    index = storm.properties.Int()

    def __init__(self, entry=None, type=None, language=None, value=None, index=None):
        self.entry = entry
        self.type = str(type) if type else None
        self.language = str(language) if language else None
        self.value = value
        self.index = index

    def as_dict(self):
        return {
            'type': self.type,
            'language': self.language,
            'value': self.value,
        }


Entry.summary = storm.references.Reference(Entry.summary_id, Content.id)
Entry.content = storm.references.ReferenceSet(Entry.id, Content.entry_id, order_by=Content.index)


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
                guid TEXT NOT NULL,
                link TEXT,
                title TEXT,
                summary_id INTEGER,
                published INTEGER,
                updated INTEGER
            )
        ''')
        store.execute('''
            CREATE TABLE content (
                id INTEGER PRIMARY KEY,
                entry_id INTEGER NOT NULL,
                type TEXT,
                language TEXT,
                value TEXT,
                `index` INTEGER NOT NULL
            )
        ''')
        store.execute('PRAGMA user_version = 1')

    store.commit()

    return database
