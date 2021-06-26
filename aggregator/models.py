from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Unicode
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship

db = SQLAlchemy()


class Feed(db.Model):
    __tablename__ = 'feeds'

    id = Column(Integer, primary_key=True, nullable=False)
    url = Column(String, unique=True, nullable=False)
    title = Column(Unicode, nullable=False)
    link = Column(String, nullable=True)
    favicon = Column(String, nullable=True)
    etag = Column(String, nullable=True)
    modified = Column(String, nullable=True)
    poll = Column(Integer, nullable=False)
    poll_status = Column(Integer, nullable=True)
    poll_type = Column(String, nullable=True)
    next_poll = Column(Integer, nullable=False, default=0)


class Entry(db.Model):
    __tablename__ = 'entries'
    __table_args__ = (
        UniqueConstraint('feed_id', 'guid'),
    )

    id = Column(Integer, primary_key=True, nullable=False)
    feed_id = Column(Integer, ForeignKey(Feed.id, ondelete='CASCADE'), nullable=False)
    guid = Column(String, nullable=False)
    poll = Column(Integer, nullable=False)
    updated = Column(DateTime, nullable=True)
    data = Column(Unicode, nullable=False)


Entry.feed = relationship(Feed)
