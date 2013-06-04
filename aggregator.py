from bottle import Bottle, request
from storm.store import Store
from persistence import open_database, Feed

import feedparser


app = Bottle()
app.database = open_database()


def success(content=None):
    """
    Creates a success response.

    @param content: optional content to be bundled with the response
    @return: a response dict
    """

    return {
        'result': 'success',
        'content': content
    }


def error(message, content=None):
    """
    Creates an error response.

    @param message: error message
    @param content: optional content to be bundled with the response
    @return: a response dict
    """

    response = {
        'result': 'error',
        'message': message
    }

    if content:
        response['content'] = content

    return response


@app.post('/feeds')
def new_feed():
    url = request.forms.get('url')
    title = request.forms.get('title')

    if not url:
        return error(-1, 'missing url parameter')

    store = Store(app.database)

    # find existing database feed for the provided url
    feed = store.find(Feed, url=url).one()

    if feed:
        return error('feed already exists', {'title': feed.title})

    data = feedparser.parse(url)

    if not data:
        return error('failed to load the feed')

    if not title:
        title = data.feed.title

    feed = store.add(Feed(url=url, title=unicode(title), etag=data.get('etag'), modified=data.get('modified')))

    # TODO: store feed entries too

    store.commit()

    return success({
        'title': feed.title
    })
