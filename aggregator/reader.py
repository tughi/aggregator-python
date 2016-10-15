from bottle import Bottle, request

from aggregator import content, utils


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
        where.append('(reader_tags | server_tags) & ? = ?')
        whereArgs.append(tags)
        whereArgs.append(tags)

    if 'without_tags' in request.query:
        tags = utils.signed_long(request.query.without_tags)
        where.append('(reader_tags | server_tags) & ? = 0')
        whereArgs.append(tags)

    if where:
        select = ' WHERE '.join((select, ' AND '.join(where)))

    select = ' ORDER BY '.join((select, 'updated' if request.query.get('order', '<') == '<' else 'updated DESC'))

    entries = []
    feeds = {}

    connection = content.open_connection()
    with content.transaction(connection) as cursor:
        for id, in cursor.execute(select, whereArgs):
            entries.append(id)

        for id, title, link, favicon, count in cursor.execute("SELECT id, title, link, favicon, (SELECT count(1) FROM entry WHERE feed_id = feed.id AND reader_tags & 1 = 0) FROM feed"):
            feeds[id] = {
                'id': id,
                'title': title,
                'link': link,
                'favicon': favicon,
                'unread': count,
            }

    return {
        'feeds': feeds,
        'entries': entries
    }

