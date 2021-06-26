# coding=utf-8
import calendar
import json
import time
from collections import OrderedDict
from urllib.parse import urlparse

import feedparser
import opml
import requests
from flask import Blueprint
from flask import current_app
from flask import jsonify
from flask import request

from aggregator import content
from aggregator.utils import signed_long

api = Blueprint('api', __name__)


class ApiException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


@api.errorhandler(ApiException)
def handle_api_exception(exception: ApiException):
    return dict(error=exception.message), exception.code


@api.get('/feeds')
def get_feeds():
    result = []

    connection = content.open_connection()
    for feed_id, feed_title, feed_url in connection.execute('SELECT id, title, url FROM feed'):
        result.append({
            'id': feed_id,
            'title': feed_title,
            'url': feed_url,
        })

    return jsonify(result)


@api.post('/feeds')
def add_feed():
    feed_url = request.form.get("url")
    if not feed_url:
        raise ApiException(400, 'the url parameter is required')

    feed_title = request.form.get("title")

    poll_time = time.localtime()
    poll = time.mktime(poll_time)

    if current_app.debug:
        print('Adding feed: %s' % feed_url)

    connection = content.open_connection()

    # find existing database feed for the provided url
    feed_exists, = connection.execute('SELECT count(1) FROM feed WHERE url = ?', [feed_url]).fetchone()

    if feed_exists:
        raise ApiException(409, 'feed already exists for this url')

    data = feedparser.parse(feed_url)

    if not data:
        raise ApiException(400, 'failed to load the feed')

    feed_title = feed_title or data.feed.get('title')
    feed_link = data.feed.get('link')
    feed_favicon = __get_favicon(feed_link or '{0}://{1}'.format(*urlparse(feed_url)))

    with content.transaction(connection) as cursor:
        cursor.execute(
            'INSERT INTO feed (url, title, link, favicon, etag, modified, poll) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (feed_url, feed_title, feed_link, feed_favicon, data.get('etag'), data.get('modified'), poll)
        )

        feed_id = cursor.lastrowid

        for entry_data in data.entries:
            guid, json_data, updated = __as_entry_data(entry_data, poll_time)

            connection.execute('INSERT INTO entry (feed_id, guid, poll, updated, data) VALUES (?, ?, ?, ?, ?)', [feed_id, guid, poll, updated, json_data])

    return {
        'id': feed_id,
        'title': feed_title,
        'url': feed_url,
    }


def __get_favicon(feed_link):
    data = feedparser.parse(feed_link)
    if data:
        for link in data.feed.get('links', []):
            if link.rel == 'shortcut icon':
                return link.href
        for link in data.feed.get('links', []):
            if link.rel == 'icon':
                return link.href

    favicon = '{0}://{1}/favicon.ico'.format(*urlparse(feed_link))
    if requests.head(favicon).status_code == 200:
        return favicon

    return None


def __as_entry_data(data, poll_time):
    link = data.get('link')

    return (
        data.get('id') or link,
        json.dumps(OrderedDict([
            ('title', data.title),
            ('link', link),
            ('author', data.get('author_detail')),
            ('summary', __as_content(data.get('summary_detail'))),
            ('content', [__as_content(content_data) for content_data in data.get('content', [])]),
            ('published', data.get('published')),
            ('updated', data.get('updated'))
        ])),
        calendar.timegm(data.get('updated_parsed') or data.get('published_parsed') or poll_time)
    )


def __as_content(data):
    return OrderedDict([
        ('type', data.type),
        ('language', data.language),
        ('value', data.value),
    ]) if data else None


@api.get('/update/feeds')
def update_feeds():
    connection = content.open_connection()

    poll_time = time.localtime()
    poll = time.mktime(poll_time)

    for feed_id, feed_url, feed_etag, feed_modified in connection.execute('SELECT id, url, etag, modified FROM feed WHERE next_poll <= ?', [poll]):
        if current_app.debug:
            print('Updating feed: %s' % feed_url)

        poll_time = time.localtime()
        poll = time.mktime(poll_time)

        data = feedparser.parse(feed_url, etag=feed_etag, modified=feed_modified)

        if not data:
            if current_app.debug:
                print('ERROR: Failed to parse feed')

            connection.execute('UPDATE feed SET poll_status = ? WHERE id = ?', [-1, feed_id])

            continue
            # with next feed

        feed_link = data.feed.get('link')
        status = data.get('status', 0)

        if status == 301:
            feed_url = data.get('href')

            if current_app.debug:
                print('Feed moved to: %s' % feed_url)

            connection.execute('UPDATE feed SET url = ? WHERE id = ?', [feed_url, feed_id])

        entries_total = len(data.entries)
        entries_updated = 0
        entries_created = 0

        for entry_data in data.entries:
            guid, json_data, updated = __as_entry_data(entry_data, poll_time)

            update_setters = ['data = ?']
            update_args = [json_data]

            if updated != poll:
                update_setters.append('updated = ?')
                update_args.append(updated)

            update_args.append(feed_id)
            update_args.append(guid)
            update_query = ' '.join(['UPDATE entry SET', ', '.join(update_setters), 'WHERE feed_id = ? AND guid = ?'])
            if connection.execute(update_query, update_args).rowcount == 0:
                # entry doesn't exist
                connection.execute('INSERT INTO entry (feed_id, guid, poll, updated, data) VALUES (?, ?, ?, ?, ?)', [feed_id, guid, poll, updated, json_data])
                entries_created += 1
            else:
                entries_updated += 1

        if current_app.debug:
            print('From %d entries, %d were updated and %d new were created' % (entries_total, entries_updated, entries_created))

        day_entries = connection.execute('SELECT COUNT(1) FROM entry WHERE feed_id = ? AND updated >= ?', [feed_id, poll - 86400]).fetchone()[0]
        week_entries = connection.execute('SELECT COUNT(1) FROM entry WHERE feed_id = ? AND updated >= ?', [feed_id, poll - 604800]).fetchone()[0]

        poll_rate = 75600 / day_entries if day_entries else 259200 / week_entries if week_entries else 345600

        if poll_rate < 1800:
            # schedule new poll in 15 minutes
            feed_poll_type = u'every 15 minutes'
            feed_next_poll = poll + 900
        elif poll_rate < 3600:
            # schedule new poll in 30 minutes
            feed_poll_type = u'every 30 minutes'
            feed_next_poll = poll + 1800
        elif poll_rate < 10800:
            # schedule new poll in 1 hour
            feed_poll_type = u'every hour'
            feed_next_poll = poll + 3600
        elif poll_rate < 21600:
            # schedule new poll in 3 hours
            feed_poll_type = u'every 3 hours'
            feed_next_poll = poll + 10800
        else:
            # schedule new poll in 6 hours
            feed_poll_type = u'every 6 hours'
            feed_next_poll = poll + 21600

        update_query = 'UPDATE feed SET poll_type = ?, next_poll = ?, link = ?, etag = ?, modified = ?, poll = ?, poll_status = ? WHERE id = ?'
        connection.execute(update_query, [feed_poll_type, feed_next_poll, feed_link, data.get('etag'), data.get('modified'), poll, status, feed_id])
    return 'OK'


@api.get('/update/favicons')
def update_favicons():
    connection = content.open_connection()
    with content.transaction(connection) as cursor:
        for feed_id, feed_url, feed_link in cursor.execute('SELECT id, url, link FROM feed'):
            if current_app.debug:
                print('Updating favicon for: %s' % feed_url)

            favicon = __get_favicon(feed_link or '{0}://{1}'.format(*urlparse(feed_url)))

            if current_app.debug:
                print('Detected favicon: %s' % favicon)

            if favicon:
                connection.execute('UPDATE feed SET favicon = ? WHERE id = ?', [favicon, feed_id])
    return 'OK'


@api.delete('/feeds/<int:feed_id>')
def delete_feed(feed_id):
    connection = content.open_connection()
    with content.transaction(connection):
        connection.execute('DELETE FROM entry WHERE feed_id = ?', [feed_id])
        connection.execute('DELETE FROM feed WHERE id = ?', [feed_id])
    return 'OK'


def import_opml(store, opml_source):
    result = []

    def import_outline(outline):
        try:
            if outline.type == 'rss':
                result.append(add_feed(store, outline.xmlUrl, outline.title))
                store.commit()
                # TODO: handle commit exceptions
        except AttributeError:
            if len(outline):
                for o in outline:
                    import_outline(o)

    outlines = opml.parse(opml_source)

    import_outline(outlines)

    return jsonify(result)


@api.get('/entries')
def get_entries():
    # validate query
    entries = OrderedDict()
    for entry_id in request.args.get('ids', '').split(','):
        if int(entry_id):
            entries[str(entry_id)] = None

    if entries:
        connection = content.open_connection()

        select = 'SELECT data, id, feed_id, updated, reader_tags, server_tags FROM entry WHERE id IN (%s)' % ', '.join(entries.keys())
        for entry_data, entry_id, feed_id, updated, reader_tags, server_tags in connection.execute(select):
            entry = json.loads(entry_data)
            entry['id'] = entry_id
            entry['feed_id'] = feed_id
            entry['updated'] = updated * 1000
            entry['reader_tags'] = reader_tags
            entry['server_tags'] = server_tags

            entries[str(entry_id)] = entry

    return jsonify(list(entries.values()))


@api.patch('/entries/<int:entry_id>')
def update_entry(entry_id):
    reader_tags = request.form.get('reader_tags')
    if reader_tags:
        reader_tags = signed_long(reader_tags)

        connection = content.open_connection()
        connection.execute('UPDATE entry SET reader_tags = ? WHERE id = ?', [reader_tags, entry_id])
    return 'OK'
