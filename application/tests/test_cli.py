"""Tests the `flask` CLI commands."""

from datetime import timedelta

from posts import POSTS, add_entries, queue, queued_entry_ids, stored_similarities
from sqlalchemy import inspect

from aggregator.models import db


def test_create_database_command_creates_the_missing_tables(app):
    db.drop_all()

    result = app.test_cli_runner().invoke(args=["create-database"])

    assert result.exit_code == 0, result.output
    assert set(inspect(db.engine).get_table_names()) == {"feeds", "entries", "entry_similarities", "entry_similarities_queue"}


def test_create_database_command_prints_the_sql_instead_of_running_it(app):
    db.drop_all()

    result = app.test_cli_runner().invoke(args=["create-database", "--sql"])

    assert result.exit_code == 0, result.output
    assert "CREATE TABLE entries (" in result.output
    assert "CREATE INDEX entries_unread ON entries (publish_time, id) WHERE read_time IS NULL;" in result.output
    assert inspect(db.engine).get_table_names() == []


def test_process_entry_similarities_command_processes_the_queue(app):
    add_entries(*POSTS)
    queue(1, 3)

    result = app.test_cli_runner().invoke(args=["process-entry-similarities"])

    assert result.exit_code == 0, result.output
    assert set(stored_similarities()) == {(1, 2), (2, 1), (3, 4), (4, 3)}
    assert queued_entry_ids() == set()


def test_process_entry_similarities_command_queues_the_entries_of_the_last_days_first(app):
    entries = list(POSTS)
    # Publishes the Artemis posts two months earlier than the others
    entries[2] = (*entries[2][:4], timedelta(days=60), False)
    entries[3] = (*entries[3][:4], timedelta(days=60, hours=1), True)
    add_entries(*entries)
    # Already queued entries are queued only once
    queue(1)

    result = app.test_cli_runner().invoke(args=["process-entry-similarities", "--enqueue-days", "30"])

    assert result.exit_code == 0, result.output
    # The Artemis posts were published before the last 30 days, so they weren't queued
    assert set(stored_similarities()) == {(1, 2), (2, 1)}
    assert queued_entry_ids() == set()
