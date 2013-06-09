import inspect
import json
import threading
import traceback
import time
from bottle import Bottle, response, request
from persistence import open_database
from storm.store import Store
import aggregator

database = open_database()

app = Bottle(autojson=False)


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
                    store.commit()
                finally:
                    store.close()
            else:
                result = callback(*args, **kwargs)

            return json.dumps(result, indent=True)

        return decorator


app.install(ServicePlugin())


@app.get('/feeds')
def feeds(store):
    return aggregator.get_feeds(store)


@app.post('/feeds')
def add_feed(store):
    url = request.forms.get('url')
    title = request.forms.get('title')

    return aggregator.add_feed(store, url, title)


@app.delete('/feeds/<feed_id:int>')
def delete_feed(store, feed_id):
    aggregator.delete_feed(store, feed_id)


@app.post('/opml/import')
def import_opml(store):
    upload = request.files.get('opml')
    print('Importing OPML file: %s' % upload.filename)
    return aggregator.import_opml(store, upload.file)


@app.get('/entries')
def entries(store):
    return aggregator.get_entries(store)


class Scheduler(threading.Thread):
    def run(self):
        while True:
            start_time = time.time()

            store = Store(database)
            aggregator.update_feeds(store)
            store.close()

            time.sleep(60 - time.time() + start_time)


if __name__ == '__main__':
    from bottle import run

    Scheduler().start()

    aggregator.DEBUG = True

    if aggregator.DEBUG:
        import storm.tracer

        class PrintStatementTracer(object):
            def connection_raw_execute(self, connection, raw_cursor, statement, params):
                if params:
                    for param in params:
                        statement = statement.replace('?', repr(param.get()), 1)
                print('STORM: %s' % statement)

        storm.tracer.install_tracer(PrintStatementTracer())

    run(app, port=4280, debug=aggregator.DEBUG)
