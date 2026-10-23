import logging
from datetime import UTC, datetime, timedelta
from typing import cast

import click
from flask import Blueprint
from sqlalchemy import CursorResult, create_mock_engine, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from aggregator import engine, similarity
from aggregator.models import Entry, EntrySimilarityQueue, db

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

blueprint = Blueprint("cli", __name__, cli_group=None)


@blueprint.cli.command("create-database")
@click.option("--sql", is_flag=True, help="Print the SQL for the database creation")
def create_database(sql: bool):
    if sql:
        logger.debug("Printing the SQL for the database creation")

        def print_statement(statement, *multiparams, **params):
            click.echo(f"{str(statement.compile(dialect=mock_engine.dialect)).strip()};\n")

        mock_engine = create_mock_engine(db.engine.url, print_statement)
        db.metadata.create_all(mock_engine, checkfirst=False)
        return

    logger.debug("Creating database")
    db.create_all()


@blueprint.cli.command("update-feeds")
def update_feeds():
    logger.debug("Updating feeds")
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

        logger.info(f"Queued {result.rowcount} entries")

    logger.debug("Processing entry similarities")
    similarity.process_queue()


@blueprint.cli.command("update-favicons")
def update_favicons():
    logger.debug("Updating favicons")
    engine.update_favicons()
