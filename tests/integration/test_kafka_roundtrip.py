"""Kafka roundtrip: producer publishes GitHub-shaped events, consumer decodes them.

Proves the message shape survives a real broker end-to-end without
exercising the external services (GitHub Events API, BigQuery) that
`poll_and_publish` / `consume_and_load` hit in production.
"""

from __future__ import annotations

from datetime import datetime
import json
import time
import uuid

from confluent_kafka import Consumer, Producer

from consumer.bq_streaming_loader import _to_row

import pytest


pytestmark = pytest.mark.integration

# How long to wait for consumer.poll() to see the produced batch before
# calling it a failure. Kafka rebalance + first-poll latency puts this at
# a few seconds; overshooting is cheap because we exit as soon as we've
# seen the expected count.
POLL_DEADLINE_S = 15.0


def _make_event(event_id: str) -> dict[str, object]:
    """Minimal GitHub-shaped event with just the fields _to_row extracts."""
    return {
        "id": event_id,
        "type": "PushEvent",
        "actor": {"login": "octocat"},
        "repo": {"name": "octocat/hello-world"},
        "created_at": "2026-09-20T10:00:00Z",
        "payload": {"action": "synchronize"},
        "public": True,
    }


def test_producer_to_consumer_roundtrip(redpanda_bootstrap: str) -> None:
    """3 published events -> 3 decoded bronze rows preserving event_id."""
    topic = f"github.events.test.{uuid.uuid4().hex[:8]}"
    event_ids = ["evt-a", "evt-b", "evt-c"]

    producer = Producer({"bootstrap.servers": redpanda_bootstrap})
    for eid in event_ids:
        producer.produce(topic, key=eid.encode(), value=json.dumps(_make_event(eid)).encode())
    producer.flush(10)

    consumer = Consumer(
        {
            "bootstrap.servers": redpanda_bootstrap,
            "group.id": f"test-{uuid.uuid4().hex[:8]}",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        },
    )
    consumer.subscribe([topic])

    rows: list[dict[str, str | None]] = []
    deadline = time.monotonic() + POLL_DEADLINE_S
    try:
        while len(rows) < len(event_ids) and time.monotonic() < deadline:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            assert msg.error() is None, msg.error()
            row = _to_row(msg.value())
            if row is not None:
                rows.append(row)
    finally:
        consumer.close()

    assert len(rows) == len(event_ids), f"expected {len(event_ids)} rows, got {len(rows)}: {rows}"
    seen_ids = {row["event_id"] for row in rows}
    assert seen_ids == set(event_ids)
    # Every row must retain the fixed shape _to_row promises.
    for row in rows:
        assert row["event_type"] == "PushEvent"
        assert row["actor_login"] == "octocat"
        assert row["repo_name"] == "octocat/hello-world"
        # ingested_at must be a valid ISO-8601 timestamp _to_row set, not
        # a passthrough of the event payload. Round-trip through datetime
        # so a bare "yes" string wouldn't accidentally pass.
        assert row["ingested_at"] is not None
        datetime.fromisoformat(row["ingested_at"])
