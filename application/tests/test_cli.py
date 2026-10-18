"""Tests the `flask` CLI commands."""

from datetime import timedelta

from posts import POSTS
from posts import add_entries
from posts import queue
from posts import queued_entry_ids
from posts import stored_similarities


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
    entries[2] = entries[2][:4] + (timedelta(days=60), False)
    entries[3] = entries[3][:4] + (timedelta(days=60, hours=1), True)
    add_entries(*entries)
    # Already queued entries are queued only once
    queue(1)

    result = app.test_cli_runner().invoke(args=["process-entry-similarities", "--enqueue-days", "30"])

    assert result.exit_code == 0, result.output
    # The Artemis posts were published before the last 30 days, so they weren't queued
    assert set(stored_similarities()) == {(1, 2), (2, 1)}
    assert queued_entry_ids() == set()
