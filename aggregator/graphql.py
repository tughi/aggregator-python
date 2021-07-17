from datetime import datetime

import graphene
import graphene_sqlalchemy
from flask import Blueprint
from flask_graphql import GraphQLView
from graphql import GraphQLError

from aggregator import engine
from aggregator.models import Entry
from aggregator.models import Feed
from aggregator.models import db


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
        return db.session.query(Entry.id).filter(Entry.feed_id == feed.id, Entry.read_time.is_(None)).count()


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


class EntryType(graphene.ObjectType):
    class Meta:
        name = Entry.__name__
        model = Entry


class Query(graphene.ObjectType):
    feeds = graphene.List(FeedType)

    @staticmethod
    def resolve_feeds(source, info):
        return Feed.query


class Mutations(graphene.ObjectType):
    refresh_feed = RefreshFeedMutation.Field()
    update_feed = UpdateFeedMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutations)

blueprint = Blueprint('graphql', __name__)
blueprint.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True))
