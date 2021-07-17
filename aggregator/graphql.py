import graphene
import graphene_sqlalchemy
from flask import Blueprint
from flask_graphql import GraphQLView
from graphql import GraphQLError

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

    @staticmethod
    def resolve_unread_entries(feed: Feed, info):
        return db.session.query(Entry.id).filter(Entry.feed_id == feed.id, Entry.read_time.is_(None)).count()


class UpdateFeedMutation(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)
        url = graphene.String()

    ok = graphene.Boolean()
    feed = graphene.Field(FeedType)

    @staticmethod
    def mutate(source, info, id: int, url: str = None):
        feed = Feed.query.get(id)
        if not feed:
            return GraphQLError("No such feed")

        url = url.strip() if url else None
        if url:
            feed.url = url

        db.session.commit()

        return dict(ok=True, feed=feed)


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
    update_feed = UpdateFeedMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutations)

blueprint = Blueprint('graphql', __name__)
blueprint.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True))
