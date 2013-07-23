from collections import OrderedDict
import json

from aggregator import content, utils

from bottle import Bottle, request


reader = Bottle()


@reader.get('/session')
def session():
    select = 'SELECT id FROM entry'

    where = []
    whereArgs = []

    if 'feed_id' in request.query:
        where.append('feed_id = ?')
        whereArgs.append(int(request.query.feed_id))

    if 'with_tags' in request.query:
        tags = utils.signed_long(request.query.with_tags)
        where.append('reader_tags & ? = ?')
        whereArgs.append(tags)
        whereArgs.append(tags)

    if 'without_tags' in request.query:
        tags = utils.signed_long(request.query.without_tags)
        where.append('reader_tags & ? = 0')
        whereArgs.append(tags)

    if where:
        select = ' WHERE '.join((select, ' AND '.join(where)))

    select = ' ORDER BY '.join((select, 'updated' if request.query.get('order', '<') == '<' else 'updated DESC'))

    entries = []
    favicons = {}

    connection = content.open_connection()
    with content.transaction(connection) as cursor:
        for row in cursor.execute(select, whereArgs):
            entries.append(row[0])

        for row in cursor.execute("SELECT id, favicon FROM feed"):
            favicons[row[0]] = row[1]

    return {
        'favicons': favicons,
        'entries': entries
    }


@reader.get('/entries')
def entries():
    # validate query
    entries = OrderedDict()
    for entry_id in request.query.get('ids').split(','):
        if int(entry_id):
            entries[str(entry_id)] = None

    if entries:
        connection = content.open_connection()

        select = 'SELECT data, id, feed_id, updated, reader_tags | server_tags FROM entry WHERE id IN (%s)' % ', '.join(entries.keys())
        for entry_data, entry_id, feed_id, updated, tags in connection.execute(select):
            entry = json.loads(unicode(entry_data))
            entry['id'] = entry_id
            entry['feed_id'] = feed_id
            entry['updated'] = updated * 1000
            entry['tags'] = tags

            entries[str(entry_id)] = entry

    return json.dumps(entries.values())
