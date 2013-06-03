from storm.locals import *

database = create_database('sqlite:aggregator.db')

store = Store(database)
store.execute('CREATE TABLE IF NOT EXISTS feed (id INTEGER PRIMARY KEY, name VARCHAR, url VARCHAR UNIQUE NOT NULL, etag VARCHAR, modified VARCHAR)')
store.commit()


class Feed(object):
    __storm_table__ = "feed"
    id = Int(primary=True)
    name = Unicode()
    url = Chars()
    etag = Chars()
    modified = Chars()



