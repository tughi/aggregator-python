import sqlite3
import os.path as path


DATABASE = path.sep.join(('databases', 'aggregator.db'))


def open_connection():
    return sqlite3.connect(DATABASE)
