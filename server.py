import inspect
import json
import traceback
from bottle import Bottle, response, request, static_file
from persistence import open_database
from storm.store import Store
import aggregator
import re

database = None

api = Bottle(autojson=False)


class ServiceException(BaseException):
    pass


class ServicePlugin(object):
    def apply(self, callback, route):
        func_args = inspect.getargspec(callback)
        requires_store = func_args and 'store' in func_args[0]

        def decorator(*args, **kwargs):
            response.headers['Content-Type'] = 'application/json'

            if requires_store:
                store = Store(database)

                try:
                    result = callback(store, *args, **kwargs)
                except BaseException, e:
                    service_exception = isinstance(e, ServiceException)

                    if not service_exception:
                        traceback.print_exc()

                    store.rollback()

                    response.status = 500
                    result = {
                        'type': 'handled' if service_exception else 'system',
                        'message': e.message
                    }
                else:
                    if store._dirty:
                        store.commit()
                finally:
                    store.close()
            else:
                result = callback(*args, **kwargs)

            return json.dumps(result, indent=True)

        return decorator


api.install(ServicePlugin())


@api.get('/feeds')
def feeds(store):
    return aggregator.get_feeds(store)


@api.post('/feeds')
def add_feed(store):
    url = request.forms.get('url')
    title = request.forms.get('title')

    return aggregator.add_feed(store, url, title)


@api.delete('/feeds/<feed_id:int>')
def delete_feed(store, feed_id):
    aggregator.delete_feed(store, feed_id)


@api.post('/opml/import')
def import_opml(store):
    upload = request.files.get('opml')
    print('Importing OPML file: %s' % upload.filename)
    return aggregator.import_opml(store, upload.file)


@api.get('/entries')
def entries(store):
    tags = request.query.get('tags')
    if tags:
        tags = re.findall(re.compile(r'([+-])([^+-]+)'), tags)
        return aggregator.get_entries(
            store,
            include=[tag for op, tag in tags if op == '+'],
            exclude=[tag for op, tag in tags if op == '-'],
        )
    return aggregator.get_entries(store)


@api.put('/entries/<entry_id:int>/tags/+<tag:int>')
def tag_entry(store, entry_id, tag):
    aggregator.tag_entry(store, entry_id, tag)


@api.put('/entries/<entry_id:int>/tags/-<tag:int>')
def untag_entry(store, entry_id, tag):
    aggregator.untag_entry(store, entry_id, tag)


@api.get('/sync/feeds')
def sync_feeds(store):
    aggregator.update_feeds(store)
    return 'ok'


@api.get('/sync/favicons')
def sync_favicons(store):
    aggregator.update_favicons(store)
    return 'ok'


server = Bottle()
server.mount('/api', api)


@server.route('/<path:path>')
def web(path):
    return static_file(path, 'web')


@server.route('/')
def entries():
    return static_file('index.html', 'web')


if __name__ == '__main__':
    from bottle import run

    database = open_database()

    aggregator.DEBUG = True

    if aggregator.DEBUG:
        import storm.tracer

        class PrintStatementTracer(object):
            def connection_raw_execute(self, connection, raw_cursor, statement, params):
                if params:
                    for param in params:
                        statement = statement.replace('?', repr(param.get() if hasattr(param, 'get') else param), 1)
                print('STORM: %s' % statement)

        storm.tracer.install_tracer(PrintStatementTracer())

    run(server, host='0.0.0.0', port=4280, debug=aggregator.DEBUG)
else:
    # uWSGI support
    import os

    os.chdir(os.path.dirname(__file__))

    database = open_database()

    application = server
