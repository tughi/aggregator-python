from flask import Blueprint
from flask import jsonify
from flask import request

from aggregator import engine
from aggregator.models import Feed

blueprint = Blueprint('api', __name__)


class ApiException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


@blueprint.errorhandler(ApiException)
def handle_api_exception(exception: ApiException):
    return dict(error=exception.message), exception.code


@blueprint.get('/feeds')
def get_feeds():
    feeds = []

    for feed in Feed.query.all():
        feeds.append({
            'id': feed.id,
            'title': feed.user_title or feed.title,
            'url': feed.url,
        })

    return jsonify(feeds)


@blueprint.post('/feeds')
def add_feed():
    feed_url = request.form.get("url")
    if not feed_url:
        raise ApiException(400, 'The url parameter is required.')

    feed_title = request.form.get("title")

    return jsonify(
        engine.add_feed(feed_url, feed_user_title=feed_title)
    )


@blueprint.get('/update/feeds')
def update_feeds():
    return jsonify(
        engine.update_feeds()
    )


@blueprint.get('/update/favicons')
def update_favicons():
    engine.update_favicons()

    return 'OK'


@blueprint.delete('/feeds/<int:feed_id>')
def delete_feed(feed_id):
    engine.delete_feed(feed_id)

    return 'OK'
