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

    with content.open_connection() as connection:
        for row in connection.execute(select, whereArgs):
            entries.append(row[0])

    return {'entries': entries}


@reader.get('/entries')
def session():
    # validate query
    entries = OrderedDict()
    for entry_id in request.query.get('ids').split(','):
        if int(entry_id):
            entries[str(entry_id)] = None

    if entries:
        with content.open_connection() as connection:
            select = 'SELECT data, id, feed_id, updated, reader_tags & server_tags FROM entry WHERE id IN (%s)' % ', '.join(entries.keys())
            for row in connection.execute(select):
                entry = json.loads(unicode(row[0]))
                entry_id = entry['id'] = row[1]
                entry['feed_id'] = row[2]
                entry['updated'] = row[3] * 1000
                entry['tags'] = row[4]

                entries[str(entry_id)] = entry

    return json.dumps(entries.values())
