import json
from datetime import datetime
from datetime import timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import TypeDecorator
from sqlalchemy import Unicode
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship

from aggregator.sanitizer import sanitize_entry_content

db = SQLAlchemy()


def epoch_datetime() -> datetime:
    return datetime.fromtimestamp(0).astimezone(timezone.utc)


class TimeStamp(TypeDecorator):
    impl = DateTime
    cache_ok = False

    TIMEZONE = datetime.utcnow().astimezone().tzinfo

    def process_bind_param(self, value: datetime, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.astimezone(self.TIMEZONE)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Feed(db.Model):
    __tablename__ = 'feeds'

    id = Column(Integer, primary_key=True, nullable=False)

    url = Column(String, unique=True, nullable=False)
    title = Column(Unicode, nullable=False)
    user_title = Column(Unicode, nullable=True)
    link = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)

    http_etag = Column(String, nullable=True)
    http_last_modified = Column(String, nullable=True)

    update_mode = Column(String, nullable=False, default='AUTO')
    last_update_time = Column(TimeStamp, nullable=False, default=epoch_datetime)
    last_update_message = Column(String, nullable=True)
    next_update_time = Column(TimeStamp, nullable=False, default=epoch_datetime)
    next_update_retry = Column(Integer, nullable=False, default=0)


class Entry(db.Model):
    __tablename__ = 'entries'
    __table_args__ = (
        UniqueConstraint('feed_id', 'uid'),
    )

    id = Column(Integer, primary_key=True, nullable=False)
    feed_id = Column(Integer, ForeignKey(Feed.id, ondelete='CASCADE'), nullable=False)

    uid = Column(String, nullable=False)
    link = Column(String, nullable=True)
    title = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    content = Column(String, nullable=True)
    author = Column(String, nullable=True)
    publish_text = Column(String, nullable=True)
    publish_time = Column(TimeStamp, nullable=True)

    insert_time = Column(TimeStamp, nullable=False)
    update_time = Column(TimeStamp, nullable=False)

    keep_time = Column(TimeStamp, nullable=True)
    read_time = Column(TimeStamp, nullable=True)
    star_time = Column(TimeStamp, nullable=True)

    @property
    def sanitized_summary(self):
        # TODO: Sanitize at aggregation time or leave it to the client. This operation has a big impact on performance.
        summary = json.loads(self.summary)
        sanitized_summary = sanitize_entry_content(summary, base_url=self.link)
        return sanitized_summary

    @property
    def sanitized_content(self):
        # TODO: Sanitize at aggregation time or leave it to the client. This operation has a big impact on performance.
        content = json.loads(self.content)
        sanitized_content = [sanitize_entry_content(_, base_url=self.link) for _ in content]
        return sanitized_content


Entry.feed = relationship(Feed)
