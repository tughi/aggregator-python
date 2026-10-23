import json
from datetime import UTC, datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, Dialect, ForeignKey, Index, TypeDecorator, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, registry, relationship

from aggregator.sanitizer.entry_content import sanitize_entry_content


class TimeStamp(TypeDecorator):
    impl = DateTime
    cache_ok = False

    TIMEZONE = datetime.now().astimezone().tzinfo

    def process_bind_param(self, value: datetime | None, dialect: Dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.astimezone(self.TIMEZONE)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class BaseModel(DeclarativeBase):
    registry = registry(type_annotation_map={datetime: TimeStamp})


def epoch_datetime() -> datetime:
    return datetime.fromtimestamp(0).astimezone(UTC)


class Feed(BaseModel):
    __tablename__ = "feeds"

    id: Mapped[int] = mapped_column(primary_key=True)

    url: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column()
    user_title: Mapped[str | None] = mapped_column()
    link: Mapped[str | None] = mapped_column()
    favicon_url: Mapped[str | None] = mapped_column()

    http_etag: Mapped[str | None] = mapped_column()
    http_last_modified: Mapped[str | None] = mapped_column()

    update_mode: Mapped[str] = mapped_column(default="AUTO")
    last_update_time: Mapped[datetime] = mapped_column(default=epoch_datetime)
    last_update_message: Mapped[str | None] = mapped_column()
    next_update_time: Mapped[datetime] = mapped_column(default=epoch_datetime)
    next_update_retry: Mapped[int] = mapped_column(default=0)


class Entry(BaseModel):
    __tablename__ = "entries"
    __table_args__ = (
        UniqueConstraint("feed_id", "uid"),
        # Indexes to speed-up the session queries
        Index("entries_unread", "publish_time", "id", postgresql_where=text("read_time IS NULL"), sqlite_where=text("read_time IS NULL")),
        Index("entries_unread_by_feed", "feed_id", "publish_time", "id", postgresql_where=text("read_time IS NULL"), sqlite_where=text("read_time IS NULL")),
        Index("entries_starred", "publish_time", "id", postgresql_where=text("star_time IS NOT NULL"), sqlite_where=text("star_time IS NOT NULL")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    feed_id: Mapped[int] = mapped_column(ForeignKey(Feed.id, ondelete="CASCADE"))
    feed: Mapped[Feed] = relationship()

    uid: Mapped[str] = mapped_column()
    link: Mapped[str | None] = mapped_column()
    title: Mapped[str | None] = mapped_column()
    summary: Mapped[str | None] = mapped_column()
    content: Mapped[str | None] = mapped_column()
    author: Mapped[str | None] = mapped_column()
    publish_text: Mapped[str | None] = mapped_column()
    publish_time: Mapped[datetime] = mapped_column()

    insert_time: Mapped[datetime] = mapped_column()
    update_time: Mapped[datetime] = mapped_column()

    keep_time: Mapped[datetime | None] = mapped_column()
    read_time: Mapped[datetime | None] = mapped_column()
    star_time: Mapped[datetime | None] = mapped_column()

    @property
    def sanitized_summary(self):
        # TODO: Sanitize at aggregation time or leave it to the client. This operation has a big impact on performance.
        summary = self.summary
        if summary is None:
            return None
        summary = json.loads(summary)
        sanitized_summary = sanitize_entry_content(summary, base_url=self.link)
        return sanitized_summary

    @property
    def sanitized_content(self):
        # TODO: Sanitize at aggregation time or leave it to the client. This operation has a big impact on performance.
        content = self.content
        if content is None:
            return None
        content = json.loads(content)
        sanitized_content = [sanitize_entry_content(_, base_url=self.link) for _ in content]
        return sanitized_content


class EntrySimilarity(BaseModel):
    __tablename__ = "entry_similarities"

    entry_id: Mapped[int] = mapped_column(ForeignKey(Entry.id, ondelete="CASCADE"), primary_key=True)
    similar_entry_id: Mapped[int] = mapped_column(ForeignKey(Entry.id, ondelete="CASCADE"), primary_key=True, index=True)
    score: Mapped[float] = mapped_column()


class EntrySimilarityQueue(BaseModel):
    __tablename__ = "entry_similarities_queue"

    entry_id: Mapped[int] = mapped_column(ForeignKey(Entry.id, ondelete="CASCADE"), primary_key=True)
    ready_time: Mapped[datetime] = mapped_column(default=epoch_datetime)


db = SQLAlchemy(model_class=BaseModel)
