import json
from collections import OrderedDict
from datetime import datetime

import sqlalchemy
from flask import Blueprint
from flask import jsonify
from flask import request

from aggregator.models import Entry
from aggregator.models import Feed
from aggregator.models import db

blueprint = Blueprint('reader', __name__)


@blueprint.get('/session')
def session():
    query = db.session.query(Entry.id)

    if 'feed_id' in request.args:
        query = query.filter(Entry.feed_id == int(request.args['feed_id']))
    if request.args.get('only_unread') == 'true':
        query = query.filter(Entry.read_time.is_(None))
    if request.args.get('only_starred') == 'true':
        query = query.filter(Entry.star_time.is_not(None))

    if request.args.get('order', '<') == '<':
        query = query.order_by(sqlalchemy.asc(Entry.publish_time))
    else:
        query = query.order_by(sqlalchemy.desc(Entry.publish_time))

    entries = []
    feeds = {}

    for entry_id, in query.all():
        entries.append(entry_id)

    unread_entries_query = db.session.query(
        Feed.id.label('feed_id'),
        sqlalchemy.func.count(1).label('unread_entries')
    ).join(Entry).filter(Entry.read_time.is_(None)).group_by(Feed.id).subquery()
    feeds_query = db.session.query(Feed, unread_entries_query.c.unread_entries).outerjoin(unread_entries_query, unread_entries_query.c.feed_id == Feed.id)

    for feed, unread_entries in feeds_query.all():
        feeds[feed.id] = {
            'id': feed.id,
            'title': feed.user_title or feed.title,
            'link': feed.link,
            'favicon': feed.favicon_url,
            'unread': unread_entries or 0,
        }

    with open('config.json') as config_file:
        config = json.load(config_file)

    return {
        'feeds': feeds,
        'entries': entries,
        'config': config,
    }


@blueprint.get('/entries')
def get_entries():
    # validate query
    entries = OrderedDict()
    for entry_id in request.args.get('ids', '').split(','):
        if int(entry_id):
            entries[str(entry_id)] = None

    if entries:
        for entry in Entry.query.filter(Entry.id.in_(entries.keys())):
            entry_data = dict(
                id=entry.id,
                feed_id=entry.feed_id,
                link=entry.link,
                title=entry.title,
                summary=entry.sanitized_summary,
                content=entry.sanitized_content,
                author=json.loads(entry.author),
                published=entry.publish_text,
                updated=int(entry.publish_time.timestamp() * 1000),
                read_flag=entry.read_time is not None,
                star_flag=entry.star_time is not None,
            )

            entries[str(entry.id)] = entry_data

    return jsonify(list(entries.values()))


@blueprint.patch('/entries/<int:entry_id>')
def update_entry(entry_id):
    entry = Entry.query.get(entry_id)

    if entry:
        read_flag = request.form.get('read_flag')
        if read_flag == 'true':
            entry.read_time = entry.read_time or datetime.utcnow()
        elif read_flag == 'false':
            entry.read_time = None

        star_flag = request.form.get('star_flag')
        if star_flag == 'true':
            entry.star_time = entry.star_time or datetime.utcnow()
        elif star_flag == 'false':
            entry.star_time = None

    db.session.commit()

    return 'OK'
