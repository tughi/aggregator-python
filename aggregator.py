import json
import traceback

from bottle import Bottle, request, response, DEBUG
from storm.store import Store
from persistence import open_database, Feed, Entry
import feedparser


app = Bottle(autojson=False)
app.database = open_database()

if DEBUG:
    import storm.tracer

    class PrintStatementTracer(object):
        def connection_raw_execute(self, connection, raw_cursor, statement, params):
            if params:
                for param in params:
                    statement = statement.replace('?', repr(param.get()), 1)
            print('STORM: %s' % statement)

    storm.tracer.install_tracer(PrintStatementTracer())


class ServiceException(BaseException):
    pass


def service(requires_store=False):
    def factory(func):
        def decorator(*args, **kwargs):
            response.headers['Content-Type'] = 'application/json'

            if requires_store:
                store = Store(app.database)

                try:
                    result = func(store, *args, **kwargs)
                except BaseException, e:
                    store.rollback()

                    service_exception = isinstance(e, ServiceException)

                    response.status = 500
                    result = {
                        'type': 'handled' if service_exception else 'system',
                        'message': e.message
                    }

                    if not service_exception:
                        traceback.print_exc()
                else:
                    store.commit()
                finally:
                    store.close()
            else:
                result = func(*args, **kwargs)

            return json.dumps(result, indent=True)

        return decorator

    return factory


@app.get('/feeds')
@service(True)
def feeds(store):
    result = []

    feeds = store.find(Feed)
    for feed in feeds:
        result.append({
            'id': feed.id,
            'title': feed.title,
            'url': feed.url
        })

    return result


@app.post('/feeds')
@service(True)
def new_feed(store):
    url = request.forms.get('url')
    title = request.forms.get('title')

    if not url:
        raise ServiceException('missing url parameter')

    # find existing database feed for the provided url
    feed = store.find(Feed, url=url).one()

    if feed:
        raise ServiceException('feed %d already exists for this url' % feed.id)

    data = feedparser.parse(url)

    if not data:
        raise ServiceException('failed to load the feed')

    feed = {
        'url': url,
        'title': unicode(title or data.feed.title),
        'etag': str(data.etag) if 'etag' in data else None,
        'modified': str(data.modified) if 'modified' in data else None,
    }
    feed = store.add(Feed(**feed))

    # TODO: store feed entries too

    store.flush()

    return {
        'id': feed.id,
        'title': feed.title
    }


@app.delete('/feeds/<feed_id:int>')
@service(True)
def delete_feed(store, feed_id):
    store.find(Entry, feed_id=feed_id).remove()
    store.find(Feed, id=feed_id).remove()
