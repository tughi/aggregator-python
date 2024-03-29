import json
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import List
from typing import Optional

import graphene
import graphene_sqlalchemy
from flask import Blueprint
from flask_graphql import GraphQLView
from graphql import GraphQLError
from sqlalchemy.sql.functions import coalesce
from sqlalchemy.sql.functions import count

from aggregator import engine
from aggregator.models import Entry
from aggregator.models import Feed
from aggregator.models import db


class AuthorType(graphene.ObjectType):
    name = graphene.String()
    href = graphene.String()
    email = graphene.String()


class ContentType(graphene.ObjectType):
    value = graphene.String()
    type = graphene.String()
    language = graphene.String()
    base = graphene.String()


class EntryType(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        name = Entry.__name__
        model = Entry

    id = graphene.Int()

    summary = graphene.Field(ContentType)
    content = graphene.List(ContentType)
    author = graphene.Field(AuthorType)

    publish_time = graphene.DateTime()

    insert_time = graphene.DateTime()
    update_time = graphene.DateTime()

    keep_time = graphene.DateTime()
    read_time = graphene.DateTime()
    star_time = graphene.DateTime()

    @staticmethod
    def resolve_author(self: Entry, info):
        return json.loads(self.author)

    @staticmethod
    def resolve_content(self: Entry, info):
        return self.sanitized_content

    @staticmethod
    def resolve_summary(self: Entry, info):
        return self.sanitized_summary


class FeedType(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        name = Feed.__name__
        model = Feed

    id = graphene.Int()
    update_time = graphene.DateTime()
    last_update_time = graphene.DateTime()
    next_update_time = graphene.DateTime()

    unread_entries = graphene.Int()

    entries_created = graphene.Int()
    entries_updated = graphene.Int()
    entries_deleted = graphene.Int()

    @staticmethod
    def resolve_unread_entries(feed: Feed, info):
        try:
            unread_entries = feed.unread_entries
        except AttributeError:
            unread_entries = Entry.query.filter(Entry.feed_id == feed.id, Entry.read_time.is_(None)).count()
        return unread_entries


@dataclass
class SessionData:
    entry_ids: List[int]
    publish_time: Optional[datetime]


class SessionType(graphene.ObjectType):
    class Meta:
        name = 'Session'

    entries = graphene.List(EntryType, limit=graphene.Int(required=True))
    entry_ids = graphene.List(graphene.Int)
    feeds = graphene.List(FeedType)
    unread_entries = graphene.Int()
    starred_entries = graphene.Int()

    @staticmethod
    def resolve_entries(session: SessionData, info, limit):
        entry_ids = session.entry_ids[:limit]
        entries = OrderedDict((entry_id, None) for entry_id in entry_ids)
        for entry in Entry.query.filter(Entry.id.in_(entry_ids)):
            entries[entry.id] = entry
        return entries.values()

    @staticmethod
    def resolve_feeds(session: SessionData, info):
        feeds = OrderedDict()
        for feed in Feed.query.order_by(coalesce(Feed.user_title, Feed.title)):
            feed.unread_entries = 0
            feeds[feed.id] = feed
        unread_entries_query = db.session.query(Feed.id, count(Entry.id)).select_from(Feed).join(Entry).filter(Entry.read_time.is_(None)).group_by(Feed.id)
        if session.publish_time:
            unread_entries_query = unread_entries_query.filter(Entry.publish_time >= session.publish_time)
        for feed_id, unread_entries in unread_entries_query:
            feeds[feed_id].unread_entries = unread_entries
        return feeds.values()

    @staticmethod
    def resolve_unread_entries(session: SessionData, info):
        query = db.session.query(Entry.id).filter(Entry.read_time.is_(None))
        if session.publish_time:
            query = query.filter(Entry.publish_time >= session.publish_time)
        return query.count()

    @staticmethod
    def resolve_starred_entries(session: SessionData, info):
        query = db.session.query(Entry.id).filter(Entry.star_time.is_not(None))
        if session.publish_time:
            query = query.filter(Entry.publish_time >= session.publish_time)
        return query.count()


class CreateFeedMutation(graphene.Mutation):
    class Arguments:
        feed_url = graphene.String(name='url', required=True)
        feed_user_title = graphene.String(name='userTitle')

    ok = graphene.Boolean()
    feed = graphene.Field(FeedType)
    feed_id = graphene.Int()

    @staticmethod
    def mutate(source, info, feed_url: str, feed_user_title: str = None):
        feed_url = feed_url.strip()

        result = engine.add_feed(feed_url, feed_user_title=feed_user_title)

        return dict(ok=True, feed_id=result['id'])

    @staticmethod
    def resolve_feed(result, info):
        return Feed.query.get(result['feed_id'])


class UpdateFeedMutation(graphene.Mutation):
    class Arguments:
        feed_id = graphene.Int(name='id', required=True)
        feed_url = graphene.String(name='url')
        feed_user_title = graphene.String(name='userTitle')

    ok = graphene.Boolean()
    feed = graphene.Field(FeedType)

    @staticmethod
    def mutate(source, info, feed_id: int, feed_url: str = None, feed_user_title: str = None):
        feed = Feed.query.get(feed_id)
        if not feed:
            return GraphQLError("No such feed")

        feed_url = feed_url.strip() if feed_url else None
        if feed_url:
            if feed_url != feed.url:
                feed.next_update_time = datetime.utcnow()
            feed.url = feed_url

        feed_user_title = feed_user_title.strip() if feed_user_title else None
        if feed_user_title:
            feed.user_title = feed_user_title

        db.session.commit()

        return dict(ok=True, feed=feed)


class RefreshFeedMutation(graphene.Mutation):
    class Arguments:
        feed_id = graphene.Int(name='id', required=True)
        forced = graphene.Boolean()

    feed = graphene.Field(FeedType)

    @staticmethod
    def mutate(source, info, feed_id: int, forced: bool = False):
        feed = Feed.query.get(feed_id)
        if not feed:
            return GraphQLError("No such feed")

        engine.update_feed(feed, forced)

        return dict(feed=feed)


class RefreshFeedFaviconMutation(graphene.Mutation):
    class Arguments:
        feed_id = graphene.Int(name='id', required=True)

    feed = graphene.Field(FeedType)

    @staticmethod
    def mutate(source, info, feed_id: int):
        feed = Feed.query.get(feed_id)
        if not feed:
            return GraphQLError("No such feed")

        engine.update_favicon(feed)

        return dict(feed=feed)


class UpdateEntryState(graphene.Mutation):
    class Arguments:
        entry_id = graphene.Int(name='id', required=True)
        keep_time = graphene.DateTime()
        read_time = graphene.DateTime()
        star_time = graphene.DateTime()

    entry = graphene.Field(EntryType)

    @staticmethod
    def mutate(source, info, entry_id: int, keep_time: datetime = None, read_time: datetime = None, star_time: datetime = None):
        entry = Entry.query.get(entry_id)
        if not entry:
            return GraphQLError("No such entry")

        entry.keep_time = keep_time
        entry.read_time = read_time
        entry.star_time = star_time

        db.session.commit()

        return dict(entry=entry)


class Query(graphene.ObjectType):
    entries = graphene.List(EntryType, entry_ids=graphene.List(graphene.Int, required=True))
    feeds = graphene.List(FeedType)
    session = graphene.Field(
        SessionType,
        feed_id=graphene.Int(),
        only_unread=graphene.Boolean(),
        only_starred=graphene.Boolean(),
        latest_first=graphene.Boolean(),
        max_age=graphene.Int(),
    )

    @staticmethod
    def resolve_entries(source, info, entry_ids=None):
        entries = OrderedDict((entry_id, None) for entry_id in entry_ids)
        for entry in Entry.query.filter(Entry.id.in_(entry_ids)):
            entries[entry.id] = entry
        return entries.values()

    @staticmethod
    def resolve_feeds(source, info):
        return Feed.query

    @staticmethod
    def resolve_session(source, info, feed_id=None, only_unread=True, only_starred=False, latest_first=False, max_age=None):
        entry_ids = db.session.query(Entry.id)
        if feed_id:
            entry_ids = entry_ids.filter(Entry.feed_id == feed_id)
        if only_unread:
            entry_ids = entry_ids.filter(Entry.read_time.is_(None))
        if only_starred:
            entry_ids = entry_ids.filter(Entry.star_time.is_not(None))
        if isinstance(max_age, int):
            publish_time = datetime.utcnow() - timedelta(days=max_age)
            entry_ids = entry_ids.filter(Entry.publish_time >= publish_time)
        else:
            publish_time = None
        entry_ids = entry_ids.order_by(Entry.publish_time.desc() if latest_first else Entry.publish_time.asc())

        return SessionData(
            entry_ids=[entry_id for entry_id, in entry_ids],
            publish_time=publish_time,
        )


class Mutations(graphene.ObjectType):
    refresh_feed = RefreshFeedMutation.Field()
    refresh_feed_favicon = RefreshFeedFaviconMutation.Field()
    create_feed = CreateFeedMutation.Field()
    update_feed = UpdateFeedMutation.Field()
    update_entry_state = UpdateEntryState.Field()


schema = graphene.Schema(query=Query, mutation=Mutations)

blueprint = Blueprint('graphql', __name__)
blueprint.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True))
