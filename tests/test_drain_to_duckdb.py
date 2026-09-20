"""Unit tests for `consumer.drain_to_duckdb` using a FakeKafkaConsumer.

The tests use a real DuckDB file in a `tmp_path` — DuckDB is a fast
in-process engine, so a real file is cheaper than mocking the driver
and gives us actual round-trip coverage of the CREATE + INSERT SQL.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

import duckdb

from consumer import drain_to_duckdb as drain_mod

from tests.fakes import FakeKafkaConsumer


if TYPE_CHECKING:
    from pathlib import Path


def _event_bytes(event_id: str, event_type: str = "PushEvent") -> bytes:
    return json.dumps(
        {
            "id": event_id,
            "type": event_type,
            "actor": {"login": "octocat"},
            "repo": {"name": "octocat/hello-world"},
            "created_at": "2026-09-20T10:00:00Z",
            "payload": {"action": "synchronize"},
        },
    ).encode()


def _mock_consumer(fake: FakeKafkaConsumer) -> object:
    return patch.object(drain_mod, "Consumer", return_value=fake)


def test_drain_to_duckdb_inserts_all_messages(tmp_path: Path) -> None:
    """3 scripted messages -> 3 bronze rows with correct event_ids."""
    db_path = str(tmp_path / "local.duckdb")
    fake = FakeKafkaConsumer(messages=[_event_bytes(f"e{i}") for i in range(3)])

    with _mock_consumer(fake):
        count = drain_mod.drain_to_duckdb("localhost:9092", "topic", db_path)

    assert count == 3
    assert fake.committed is True
    assert fake.closed is True

    conn = duckdb.connect(db_path, read_only=True)
    try:
        rows = conn.sql("select event_id, event_type from bronze.raw_events order by event_id").fetchall()
    finally:
        conn.close()
    assert rows == [("e0", "PushEvent"), ("e1", "PushEvent"), ("e2", "PushEvent")]


def test_drain_to_duckdb_empty_topic_returns_zero(tmp_path: Path) -> None:
    """No messages -> zero rows inserted, no commit."""
    db_path = str(tmp_path / "local.duckdb")
    fake = FakeKafkaConsumer(messages=[])

    with _mock_consumer(fake):
        count = drain_mod.drain_to_duckdb("localhost:9092", "topic", db_path)

    assert count == 0
    # No commit when there's nothing to insert — offsets stay put.
    assert fake.committed is False
    assert fake.closed is True


def test_drain_to_duckdb_respects_max_messages(tmp_path: Path) -> None:
    """`max_messages` caps the drain; remainder stays on the topic (uncommitted)."""
    db_path = str(tmp_path / "local.duckdb")
    fake = FakeKafkaConsumer(messages=[_event_bytes(f"e{i}") for i in range(5)])

    with _mock_consumer(fake):
        first = drain_mod.drain_to_duckdb("localhost:9092", "topic", db_path, max_messages=2)
    assert first == 2

    # A follow-up drain (simulating the next Dagster materialization)
    # picks up the remaining 3 — observable behavior, not an
    # implementation-detail peek at `fake.messages`.
    with _mock_consumer(fake):
        second = drain_mod.drain_to_duckdb("localhost:9092", "topic", db_path)
    assert second == 3


def test_drain_to_duckdb_skips_non_json_messages(tmp_path: Path) -> None:
    """Malformed JSON is logged and dropped; valid messages still land."""
    db_path = str(tmp_path / "local.duckdb")
    fake = FakeKafkaConsumer(messages=[b"{not-json", _event_bytes("valid")])

    with _mock_consumer(fake):
        count = drain_mod.drain_to_duckdb("localhost:9092", "topic", db_path)

    assert count == 1
    conn = duckdb.connect(db_path, read_only=True)
    try:
        row = conn.sql("select event_id from bronze.raw_events").fetchone()
    finally:
        conn.close()
    assert row == ("valid",)


def test_drain_to_duckdb_creates_schema_on_first_call(tmp_path: Path) -> None:
    """Fresh DuckDB file -> `bronze` schema + `raw_events` table auto-created."""
    db_path = str(tmp_path / "local.duckdb")
    fake = FakeKafkaConsumer(messages=[_event_bytes("only")])

    with _mock_consumer(fake):
        drain_mod.drain_to_duckdb("localhost:9092", "topic", db_path)

    conn = duckdb.connect(db_path, read_only=True)
    try:
        schemas = {row[0] for row in conn.sql("select schema_name from information_schema.schemata").fetchall()}
    finally:
        conn.close()
    assert "bronze" in schemas
