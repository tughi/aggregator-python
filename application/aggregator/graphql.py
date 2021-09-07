import json
from collections import OrderedDict
from datetime import datetime

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


class ContentType(graphene.ObjectType):
    type = graphene.String()
    language = graphene.String()
    value = graphene.String()


class EntryType(graphene_sqlalchemy.SQLAlchemyObjectType):
    class Meta:
        name = Entry.__name__
        model = Entry

    id = graphene.Int()

    summary = graphene.Field(ContentType)
    content = graphene.List(ContentType)

    publish_time = graphene.DateTime()

    insert_time = graphene.DateTime()
    update_time = graphene.DateTime()

    read_time = graphene.DateTime()
    star_time = graphene.DateTime()

    def resolve_content(self: Entry, info):
        return json.loads(self.content)

    def resolve_summary(self: Entry, info):
        return json.loads(self.summary)


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


class SessionType(graphene.ObjectType):
    class Meta:
        name = 'Session'

    entries = graphene.List(EntryType, first=graphene.Int(required=True))
    entry_ids = graphene.List(graphene.Int)
    feeds = graphene.List(FeedType)

    @staticmethod
    def resolve_entries(session: dict, info, first):
        entry_ids = session.get('entry_ids', [])[:first]
        entries = OrderedDict((entry_id, None) for entry_id in entry_ids)
        for entry in Entry.query.filter(Entry.id.in_(entry_ids)):
            entries[entry.id] = entry
        return entries.values()


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


class Query(graphene.ObjectType):
    entries = graphene.List(EntryType, entry_ids=graphene.List(graphene.Int, required=True))
    feeds = graphene.List(FeedType)
    session = graphene.Field(SessionType, feed_id=graphene.Int(), only_unread=graphene.Boolean(), only_starred=graphene.Boolean())

    @staticmethod
    def resolve_entries(source, info, entry_ids=None):
        return Entry.query.filter(Entry.id.in_(entry_ids))

    @staticmethod
    def resolve_feeds(source, info):
        return Feed.query

    @staticmethod
    def resolve_session(source, info, feed_id=None, only_unread=True, only_starred=False):
        entry_ids = db.session.query(Entry.id)
        if feed_id:
            entry_ids = entry_ids.filter(Entry.feed_id == feed_id)
        if only_unread:
            entry_ids = entry_ids.filter(Entry.read_time.is_(None))
        if only_starred:
            entry_ids = entry_ids.filter(Entry.star_time.is_not(None))

        feeds = OrderedDict((feed.id, feed) for feed in Feed.query.order_by(coalesce(Feed.user_title, Feed.title)))
        unread_entries_query = db.session.query(Feed.id, count(Entry.id)).select_from(Feed).join(Entry).filter(Entry.read_time.is_(None)).group_by(Feed.id)
        for feed_id, unread_entries in unread_entries_query:
            feeds[feed_id].unread_entries = unread_entries

        return dict(
            entry_ids=[entry_id for entry_id, in entry_ids],
            feeds=feeds.values(),
        )


class Mutations(graphene.ObjectType):
    refresh_feed = RefreshFeedMutation.Field()
    refresh_feed_favicon = RefreshFeedFaviconMutation.Field()
    update_feed = UpdateFeedMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutations)

blueprint = Blueprint('graphql', __name__)
blueprint.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True))
