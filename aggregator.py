from bottle import Bottle, request, response
from storm.store import Store
from persistence import open_database, Feed, Entry

import feedparser


app = Bottle()
app.database = open_database()


if True:
    # debug mode

    import storm.tracer

    class PrintStatementTracer(object):
        def connection_raw_execute(self, connection, raw_cursor, statement, params):
            if params:
                for param in params:
                    statement = statement.replace('?', repr(param.get()), 1)
            print('STORM: %s' % statement)

    storm.tracer.install_tracer(PrintStatementTracer())


@app.get('/feeds')
def feeds():
    result = []

    store = Store(app.database)

    feeds = store.find(Feed)
    for feed in feeds:
        result.append({
            'id': feed.id,
            'title': feed.title,
            'url': feed.url
        })

    return result


@app.post('/feeds')
def new_feed():
    url = request.forms.get('url')
    title = request.forms.get('title')

    if not url:
        response.status = 400
        return 'missing url parameter'

    store = Store(app.database)

    # find existing database feed for the provided url
    feed = store.find(Feed, url=url).one()

    if feed:
        response.status = 409
        return 'a feed already exists with this url: %d' % feed.id

    data = feedparser.parse(url)

    if not data:
        response.status = 400
        return 'failed to load the feed'

    feed = {
        'url': url,
        'title': unicode(title or data.feed.title),
        'etag': str(data.etag) if 'etag' in data else None,
        'modified': str(data.modified) if 'modified' in data else None,
    }
    feed = store.add(Feed(**feed))

    # TODO: store feed entries too

    store.commit()

    return {
        'id': feed.id,
        'title': feed.title
    }


@app.delete('/feeds/<id:int>')
def delete_feed(id):
    store = Store(app.database)
    try:
        store.find(Entry, feed_id=id).remove()
        store.find(Feed, id=id).remove()
    except RuntimeError:
        store.rollback()

        response.status = 409
        return e.args
    else:
        store.commit()
    return
