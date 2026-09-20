"""Unit tests for `consumer.bq_streaming_loader` helpers."""

from __future__ import annotations

import json

from consumer.bq_streaming_loader import _to_row


def _event(**overrides: object) -> dict[str, object]:
    """Build a synthetic GitHub event payload with sensible defaults."""
    base: dict[str, object] = {
        "id": "42",
        "type": "PushEvent",
        "actor": {"login": "octocat"},
        "repo": {"name": "octocat/hello"},
        "created_at": "2026-01-01T00:00:00Z",
        "payload": {"action": "opened"},
        "public": True,
    }
    base.update(overrides)
    return base


def test_to_row_extracts_flat_fields() -> None:
    """Happy path: all seven bronze columns get populated from the event."""
    row = _to_row(json.dumps(_event()).encode())

    assert row is not None
    assert row["event_id"] == "42"
    assert row["event_type"] == "PushEvent"
    assert row["actor_login"] == "octocat"
    assert row["repo_name"] == "octocat/hello"
    assert row["event_created_at"] == "2026-01-01T00:00:00Z"
    assert row["ingested_at"] is not None
    # payload round-trips as a JSON string
    assert json.loads(row["payload"])["id"] == "42"


def test_to_row_returns_none_on_bad_json() -> None:
    """Malformed bytes return None (they get skipped, not raised)."""
    assert _to_row(b"{not-json") is None


def test_to_row_tolerates_missing_actor_and_repo() -> None:
    """When `actor` / `repo` are absent, the corresponding columns are None."""
    row = _to_row(json.dumps(_event(actor=None, repo=None)).encode())

    assert row is not None
    assert row["actor_login"] is None
    assert row["repo_name"] is None
    # Non-nested fields still populate.
    assert row["event_id"] == "42"


def test_to_row_ignores_non_string_ids() -> None:
    """Integer-typed values from odd events are coerced to None, not raised."""
    row = _to_row(json.dumps(_event(id=42, type=None)).encode())

    assert row is not None
    assert row["event_id"] is None
    assert row["event_type"] is None


def test_to_row_ignores_non_dict_actor() -> None:
    """`actor` being a scalar (never observed but valid JSON) is safe."""
    row = _to_row(json.dumps(_event(actor="not-a-dict")).encode())

    assert row is not None
    assert row["actor_login"] is None
