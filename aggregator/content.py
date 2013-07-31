# coding=utf-8
import sqlite3
from os import path


DATABASE = path.sep.join(('databases', 'aggregator.db'))


class transaction(object):
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        self.connection.execute('BEGIN')
        return self.connection.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_tb is None:
            self.connection.execute('COMMIT')
        else:
            self.connection.execute('ROLLBACK')


def open_connection():
    connection = sqlite3.connect(DATABASE, isolation_level=None)

    version = connection.execute('PRAGMA user_version').fetchone()[0]
    VERSION = 3

    if version < VERSION:
        with transaction(connection) as cursor:
            if version == 0:
                __create_schema(cursor)
            else:
                __upgrade_schema(cursor, version)

            cursor.execute('PRAGMA user_version = %d' % VERSION)

    return connection


def __create_schema(cursor):
    cursor.execute('''
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
    cursor.execute('''
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
    cursor.execute('''
        CREATE TABLE tag (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            flag INTEGER UNIQUE NOT NULL
        )
    ''')
    cursor.executemany('INSERT INTO tag VALUES (?, ?, ?)', [
        (1, 'read', 1),
        (2, 'star', 2),
    ])


def __upgrade_schema(cursor, version):
    # upgrade schema
    if version <= 1:
        cursor.execute('ALTER TABLE feed ADD COLUMN favicon TEXT')

    if version <= 2:
        cursor.execute('''
            CREATE TABLE tag (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                flag INTEGER UNIQUE NOT NULL
            )
        ''')
        cursor.executemany('INSERT INTO tag VALUES (?, ?, ?)', [
            (1, 'read', 1),
            (2, 'star', 2),
        ])

        # migrate the entry table
        cursor.execute('ALTER TABLE entry RENAME TO old_entry')
        cursor.execute('''
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
        cursor.execute('''
            INSERT INTO entry
                SELECT
                    id, feed_id, guid, poll, updated, data, like('%|read|%', reader_tags) | CASE like('%|star|%', reader_tags) WHEN 1 THEN 2 ELSE 0 END, 0
                FROM old_entry
        ''')
        cursor.execute('DROP TABLE old_entry')

