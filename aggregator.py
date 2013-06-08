import json
import traceback
from time import mktime
import inspect

from bottle import Bottle, request, response, DEBUG
from storm.store import Store
from storm.expr import Select
from persistence import open_database, Feed, Entry, Content
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


def service(func):
    func_args = inspect.getargspec(func)
    requires_store = func_args and 'store' in func_args[0]

    def decorator(*args, **kwargs):
        response.headers['Content-Type'] = 'application/json'

        if requires_store:
            store = Store(app.database)

            try:
                result = func(store, *args, **kwargs)
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
            result = func(*args, **kwargs)

        return json.dumps(result, indent=True)

    return decorator


@app.get('/feeds')
@service
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
@service
def new_feed(store):
    url = request.forms.get('url')
    title = request.forms.get('title')

    if not url:
        raise ServiceException('missing url parameter')

    # find existing database feed for the provided url
    store_feed = store.find(Feed, url=url).one()

    if store_feed:
        raise ServiceException('feed %d already exists for this url' % store_feed.id)

    data = feedparser.parse(url)

    if not data:
        raise ServiceException('failed to load the feed')

    store_feed = store.add(Feed(
        url=url,
        title=title or data.feed.title,
        etag=data.get('etag'),
        modified=data.get('modified')
    ))

    for entry in data.entries:
        store_entry = store.add(Entry(
            id=entry.id,
            feed=store_feed,
            link=entry.link,
            title=entry.title,
            published=mktime(entry.published_parsed),
            updated=mktime(entry.updated_parsed)
        ))

        store.flush()

        summary = entry.get('summary_detail')
        if summary:
            store_entry.summary = store.add(Content(
                entry=store_entry,
                type=summary.type,
                language=summary.language,
                value=summary.value,
                index=-1
            ))

        for index, content in enumerate(entry.get('content', [])):
            store.add(Content(
                entry=store_entry,
                type=content.type,
                language=content.language,
                value=content.value,
                index=index
            ))

    return {
        'id': store_feed.id,
        'title': store_feed.title
    }


@app.delete('/feeds/<feed_id:int>')
@service
def delete_feed(store, feed_id):
    store.find(Content, Content.id.is_in(
        Select(Content.id, (Content.entry_id == Entry.id) & (Entry.feed_id == feed_id)))).remove()
    store.find(Entry, feed_id=feed_id).remove()
    store.find(Feed, id=feed_id).remove()


@app.get('/entries')
@service
def entries(store):
    result = []

    def content_to_dict(content):
        return {
            'type': content.type,
            'language': content.language,
            'value': content.value,
        }

    for entry in store.find(Entry).order_by(Entry.published):
        result.append({
            'id': entry.id,
            'title': entry.title,
            'link': entry.link,
            'summary': content_to_dict(entry.summary) if entry.summary else None,
            'content': [content_to_dict(content) for content in entry.content.find(Content.index >= 0)]
        })

    return result


if __name__ == '__main__':
    from bottle import run

    run(app, port=4280)
