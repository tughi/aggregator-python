# coding=utf-8
import json
import sqlite3


def open_connection():
    connection = sqlite3.connect('aggregator.db', isolation_level=None)

    version = connection.execute('PRAGMA user_version').fetchone()[0]
    VERSION = 3

    if version < VERSION:
        connection.execute('BEGIN')

        try:
            if version == 0:
                __create_schema(connection)
            else:
                __upgrade_schema(connection, version)

            connection.execute('PRAGMA user_version = %d' % VERSION)
            connection.execute('COMMIT')
        except:
            connection.execute('ROLLBACK')
            raise

    return connection


def __create_schema(connection):
    connection.execute('''
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
    connection.execute('''
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
    connection.execute('''
        CREATE TABLE tag (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            flag INTEGER UNIQUE NOT NULL
        )
    ''')
    connection.executemany('INSERT INTO tag VALUES (?, ?, ?)', [
        (1, 'read', 1),
        (2, 'star', 2),
    ])



def __upgrade_schema(connection, version):
    # upgrade schema
    if version <= 1:
        connection.execute('ALTER TABLE feed ADD COLUMN favicon TEXT')

    if version <= 2:
        connection.execute('''
            CREATE TABLE tag (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                flag INTEGER UNIQUE NOT NULL
            )
        ''')
        connection.executemany('INSERT INTO tag VALUES (?, ?, ?)', [
            (1, 'read', 1),
            (2, 'star', 2),
        ])

        # migrate the entry table
        connection.execute('ALTER TABLE entry RENAME TO old_entry')
        connection.execute('''
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
        connection.execute('''
            INSERT INTO entry
                SELECT
                    id, feed_id, guid, poll, updated, data, like('%|read|%', reader_tags) | CASE like('%|star|%', reader_tags) WHEN 1 THEN 2 ELSE 0 END, 0
                FROM old_entry
        ''')
        connection.execute('DROP TABLE old_entry')

