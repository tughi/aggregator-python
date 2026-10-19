from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Self, TypedDict

import strawberry
from flask import Blueprint, request
from graphql import GraphQLError
from sqlalchemy.sql.functions import coalesce, count
from strawberry.flask.views import GraphQLView

from aggregator import engine, models
from aggregator.models import db
from aggregator.sanitizer.entry_content import ContentData


class AuthorData(TypedDict, total=False):
    name: str
    href: str
    email: str


@strawberry.type
class Author:
    name: str | None = None
    href: str | None = None
    email: str | None = None

    @classmethod
    def from_author(cls, author: AuthorData) -> Author:
        return cls(name=author.get("name"), href=author.get("href"), email=author.get("email"))


@strawberry.type
class Content:
    value: str
    type: str
    language: str | None

    @classmethod
    def from_content(cls, content: ContentData) -> Content:
        return cls(value=content["value"], type=content["type"], language=content["language"])


@strawberry.type
class BaseEntry:
    id: int
    feed_id: int
    uid: str
    link: str | None
    title: str | None
    publish_text: str | None
    publish_time: datetime
    insert_time: datetime
    update_time: datetime
    keep_time: datetime | None
    read_time: datetime | None
    star_time: datetime | None
    model: strawberry.Private[models.Entry]

    @classmethod
    def from_model(cls, entry: models.Entry) -> Self:
        return cls(
            id=entry.id,
            feed_id=entry.feed_id,
            uid=entry.uid,
            link=entry.link,
            title=entry.title,
            publish_text=entry.publish_text,
            publish_time=entry.publish_time,
            insert_time=entry.insert_time,
            update_time=entry.update_time,
            keep_time=entry.keep_time,
            read_time=entry.read_time,
            star_time=entry.star_time,
            model=entry,
        )

    @strawberry.field
    def summary(self) -> Content | None:
        summary = self.model.sanitized_summary
        return Content.from_content(summary) if summary else None

    @strawberry.field
    def content(self) -> list[Content]:
        return [Content.from_content(content) for content in self.model.sanitized_content]

    @strawberry.field
    def author(self) -> Author | None:
        author = json.loads(self.model.author)
        return Author.from_author(author) if author else None

    @strawberry.field
    def feed(self) -> Feed:
        return Feed.from_model(self.model.feed)


@strawberry.type
class SimilarEntry(BaseEntry):
    pass


@strawberry.type
class Entry(BaseEntry):
    @strawberry.field(description="Unread entries that likely cover the same story as this one, most similar first. Runs a database query per entry.")
    def similar_entries(self, limit: int = 5, min_score: float = 0.3) -> list[SimilarEntry]:
        entries = (
            models.Entry.query.join(models.EntrySimilarity, models.EntrySimilarity.similar_entry_id == models.Entry.id)
            .filter(
                models.EntrySimilarity.entry_id == self.id,
                models.EntrySimilarity.score >= min_score,
                models.Entry.read_time.is_(None),
            )
            .order_by(models.EntrySimilarity.score.desc())
            .limit(limit)
        )
        return [SimilarEntry.from_model(entry) for entry in entries]


@strawberry.type
class Feed:
    id: int
    url: str
    title: str
    user_title: str | None
    link: str | None
    favicon_url: str | None
    http_etag: str | None
    http_last_modified: str | None
    update_mode: str
    last_update_time: datetime
    last_update_message: str | None
    next_update_time: datetime
    next_update_retry: int
    entries_created: int | None = None
    entries_updated: int | None = None
    known_unread_entries: strawberry.Private[int | None] = None

    @classmethod
    def from_model(cls, feed: models.Feed, **fields) -> Feed:
        return cls(
            id=feed.id,
            url=feed.url,
            title=feed.title,
            user_title=feed.user_title,
            link=feed.link,
            favicon_url=feed.favicon_url,
            http_etag=feed.http_etag,
            http_last_modified=feed.http_last_modified,
            update_mode=feed.update_mode,
            last_update_time=feed.last_update_time,
            last_update_message=feed.last_update_message,
            next_update_time=feed.next_update_time,
            next_update_retry=feed.next_update_retry,
            **fields,
        )

    @strawberry.field
    def unread_entries(self) -> int:
        if self.known_unread_entries is not None:
            return self.known_unread_entries
        return models.Entry.query.filter(models.Entry.feed_id == self.id, models.Entry.read_time.is_(None)).count()


def entries_by_id(entry_ids: list[int | None]) -> list[Entry | None]:
    entries = {entry.id: entry for entry in models.Entry.query.filter(models.Entry.id.in_(entry_ids))}
    return [Entry.from_model(entries[entry_id]) if entry_id in entries else None for entry_id in entry_ids]


@strawberry.type
class Session:
    entry_ids: list[int]
    publish_time: strawberry.Private[datetime | None]

    @strawberry.field
    def entries(self, limit: int) -> list[Entry]:
        return [entry for entry in entries_by_id(self.entry_ids[:limit]) if entry]

    @strawberry.field
    def feeds(self) -> list[Feed]:
        unread_entries_query = (
            db.session.query(models.Feed.id, count(models.Entry.id))
            .select_from(models.Feed)
            .join(models.Entry)
            .filter(models.Entry.read_time.is_(None))
            .group_by(models.Feed.id)
        )
        if self.publish_time:
            unread_entries_query = unread_entries_query.filter(models.Entry.publish_time >= self.publish_time)
        unread_entries = dict(unread_entries_query.all())
        return [
            Feed.from_model(feed, known_unread_entries=unread_entries.get(feed.id, 0))
            for feed in models.Feed.query.order_by(coalesce(models.Feed.user_title, models.Feed.title))
        ]

    @strawberry.field
    def unread_entries(self) -> int:
        query = db.session.query(models.Entry.id).filter(models.Entry.read_time.is_(None))
        if self.publish_time:
            query = query.filter(models.Entry.publish_time >= self.publish_time)
        return query.count()

    @strawberry.field
    def starred_entries(self) -> int:
        query = db.session.query(models.Entry.id).filter(models.Entry.star_time.is_not(None))
        if self.publish_time:
            query = query.filter(models.Entry.publish_time >= self.publish_time)
        return query.count()


@strawberry.type
class CreateFeedResult:
    ok: bool
    feed: Feed
    feed_id: int


@strawberry.type
class UpdateFeedResult:
    ok: bool
    feed: Feed


@strawberry.type
class RefreshFeedResult:
    feed: Feed


@strawberry.type
class RefreshFeedFaviconResult:
    feed: Feed


@strawberry.type
class UpdateEntryStateResult:
    entry: Entry


@strawberry.type
class DeleteFeedResult:
    ok: bool


def get_feed(id: int) -> models.Feed:
    feed = db.session.get(models.Feed, id)
    if not feed:
        raise GraphQLError("No such feed")
    return feed


@strawberry.type
class Mutations:
    @strawberry.mutation(description="Deletes a feed together with all its entries.")
    def delete_feed(self, id: int) -> DeleteFeedResult | None:
        get_feed(id)

        engine.delete_feed(id)

        return DeleteFeedResult(ok=True)

    @strawberry.mutation
    def refresh_feed(self, id: int, forced: bool = False) -> RefreshFeedResult | None:
        feed = get_feed(id)

        result = engine.update_feed(feed, forced)
        entries = result["entries"] if result else {}

        return RefreshFeedResult(feed=Feed.from_model(feed, entries_created=entries.get("created"), entries_updated=entries.get("updated")))

    @strawberry.mutation
    def refresh_feed_favicon(self, id: int) -> RefreshFeedFaviconResult | None:
        feed = get_feed(id)

        engine.update_favicon(feed)

        return RefreshFeedFaviconResult(feed=Feed.from_model(feed))

    @strawberry.mutation
    def create_feed(self, url: str, user_title: str | None = None) -> CreateFeedResult | None:
        result = engine.add_feed(url.strip(), feed_user_title=user_title)

        return CreateFeedResult(ok=True, feed_id=result["id"], feed=Feed.from_model(get_feed(result["id"])))

    @strawberry.mutation
    def update_feed(self, id: int, url: str | None = None, user_title: str | None = None) -> UpdateFeedResult | None:
        feed = get_feed(id)

        url = url.strip() if url else None
        if url and not engine.web_url_or_none(url):
            raise GraphQLError(engine.NOT_A_WEB_URL_MESSAGE)
        if url:
            if url != feed.url:
                feed.next_update_time = datetime.now(tz=UTC)
            feed.url = url

        user_title = user_title.strip() if user_title else None
        if user_title:
            feed.user_title = user_title

        db.session.commit()

        return UpdateFeedResult(ok=True, feed=Feed.from_model(feed))

    @strawberry.mutation
    def update_entry_state(
        self,
        id: int,
        keep_time: datetime | None = None,
        read_time: datetime | None = None,
        star_time: datetime | None = None,
    ) -> UpdateEntryStateResult | None:
        entry = db.session.get(models.Entry, id)
        if not entry:
            raise GraphQLError("No such entry")

        entry.keep_time = keep_time
        entry.read_time = read_time
        entry.star_time = star_time

        db.session.commit()

        return UpdateEntryStateResult(entry=Entry.from_model(entry))


@strawberry.type
class Query:
    @strawberry.field
    def entries(self, entry_ids: list[int | None]) -> list[Entry | None]:
        return entries_by_id(entry_ids)

    @strawberry.field
    def feeds(self) -> list[Feed]:
        return [Feed.from_model(feed) for feed in models.Feed.query]

    @strawberry.field(description="A feed's entries, newest first. `read` limits them to read (true) or unread (false) entries.")
    def feed_entries(self, feed_id: int, read: bool | None = None, limit: int = 50, offset: int = 0) -> list[Entry]:
        get_feed(feed_id)

        entries = models.Entry.query.filter(models.Entry.feed_id == feed_id)
        if read is True:
            entries = entries.filter(models.Entry.read_time.is_not(None))
        elif read is False:
            entries = entries.filter(models.Entry.read_time.is_(None))
        entries = entries.order_by(models.Entry.publish_time.desc(), models.Entry.id.desc()).offset(offset).limit(limit)

        return [Entry.from_model(entry) for entry in entries]

    @strawberry.field
    def session(
        self,
        feed_id: int | None = None,
        only_unread: bool = True,
        only_starred: bool = False,
        latest_first: bool = False,
        max_age: int | None = None,
    ) -> Session:
        entry_ids = db.session.query(models.Entry.id)
        if feed_id:
            entry_ids = entry_ids.filter(models.Entry.feed_id == feed_id)
        if only_unread:
            entry_ids = entry_ids.filter(models.Entry.read_time.is_(None))
        if only_starred:
            entry_ids = entry_ids.filter(models.Entry.star_time.is_not(None))
        if max_age is not None:
            publish_time = datetime.now(tz=UTC) - timedelta(days=max_age)
            entry_ids = entry_ids.filter(models.Entry.publish_time >= publish_time)
        else:
            publish_time = None
        if latest_first:
            entry_ids = entry_ids.order_by(models.Entry.publish_time.desc(), models.Entry.id.desc())
        else:
            entry_ids = entry_ids.order_by(models.Entry.publish_time.asc(), models.Entry.id.asc())

        return Session(entry_ids=[entry_id for (entry_id,) in entry_ids], publish_time=publish_time)


schema = strawberry.Schema(query=Query, mutation=Mutations)

blueprint = Blueprint("graphql", __name__)


@blueprint.before_request
def reject_cross_site_requests():
    """
    Protects mutations against CSRF.

    Browsers let any site submit a form to this endpoint, with the user's credentials attached. Requiring a JSON body
    forces cross-site requests through a CORS preflight, which fails because the app doesn't allow other origins.
    Sec-Fetch-Site additionally rejects requests the browser marks as coming from another site.
    """
    if request.method != "POST":
        return None
    if request.mimetype != "application/json":
        return {"errors": [{"message": "Content-Type must be application/json"}]}, 415
    if request.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
        return {"errors": [{"message": "Cross-site requests are not allowed"}]}, 403
    return None


blueprint.add_url_rule("/graphql", view_func=GraphQLView.as_view("graphql", schema=schema))
