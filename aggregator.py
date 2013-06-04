from bottle import Bottle, request
from storm.store import Store
from persistence import open_database, Feed

import feedparser


app = Bottle()
app.database = open_database()


def success(result=None):
    """
    Creates a success response.

    @param result: optional data to be bundled with the response
    @return: a response dict
    """

    return {
        'result': 'success',
        'content': result
    }


def error(code, message):
    """
    Creates an error response.

    @param code: error code
    @param message: error message
    @return: a response dict
    """

    return {
        'result': 'error',
        'content': {
            'code': code,
            'message': message
        }
    }


@app.post('/feeds')
def new_feed():
    url = request.forms.get('url')
    title = request.forms.get('title')

    if not url:
        return error(-1, 'missing url parameter')

    # TODO: create temporary database feed + entries

    if not title:
        # validate the provided feed url

        data = feedparser.parse(url)

        # TODO: handle parser errors

        return success({
            'title': data.feed.title
        })
    else:
        # create database feed

        store = Store(app.database)
        store.add(Feed(url, unicode(title)))
        store.commit()

        return success()
