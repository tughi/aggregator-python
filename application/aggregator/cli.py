import logging
from datetime import UTC, datetime, timedelta
from typing import cast

import click
from flask import Blueprint
from sqlalchemy import CursorResult, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from aggregator import content, engine, similarity
from aggregator.models import Entry, EntrySimilarityQueue, db

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

blueprint = Blueprint("cli", __name__, cli_group=None)


@blueprint.cli.command("create-database")
def create_database():
    db.create_all()


@blueprint.cli.command("restore")
@click.argument("file", type=click.File("r"))
def restore(file):
    content.restore(file)


@blueprint.cli.command("update-feeds")
def update_feeds():
    logger.info("Updating feeds")
    engine.update_feeds()


@blueprint.cli.command("process-entry-similarities")
@click.option("--enqueue-days", default=0, show_default=True, help="Queue the entries published in the last DAYS days first.")
def process_entry_similarities(enqueue_days: int) -> None:
    if enqueue_days > 0:
        match db.engine.dialect.name:
            case "postgresql":
                insert = postgresql_insert
            case "sqlite":
                insert = sqlite_insert
            case _:
                raise RuntimeError("Unsupported database dialect")

        statement = (
            insert(EntrySimilarityQueue)
            .from_select(["entry_id"], select(Entry.id).where(Entry.publish_time >= datetime.now(tz=UTC) - timedelta(days=enqueue_days)))
            .on_conflict_do_nothing()
        )

        result = cast(CursorResult, db.session.execute(statement))
        db.session.commit()

        logger.info(f"Queued {result.rowcount} entries published in the last {enqueue_days} days")

    similarity.process_queue()


@blueprint.cli.command("update-favicons")
def update_favicons():
    logger.info("Updating favicons")
    engine.update_favicons()
