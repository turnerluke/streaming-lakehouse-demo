"""Consume GitHub events from Kafka and stream-insert them into BigQuery bronze.

The bronze table stores the payload as a single JSON column plus a few
extracted columns for partitioning and clustering. All silver/gold shaping
happens in dbt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
import os
import signal
import sys
from typing import TYPE_CHECKING

from confluent_kafka import Consumer, KafkaException
from dotenv import load_dotenv
from google.cloud import bigquery


if TYPE_CHECKING:
    from types import FrameType


type JsonValue = bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"] | None
type JsonObject = dict[str, JsonValue]
type BronzeRow = dict[str, str | None]

load_dotenv()

log = logging.getLogger("consumer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
TOPIC = os.environ.get("KAFKA_TOPIC_EVENTS", "github.events")
PROJECT = os.environ["GCP_PROJECT_ID"]
DATASET = os.environ.get("BQ_DATASET_BRONZE", "bronze")
TABLE = "raw_events"
BATCH_SIZE = 200
BATCH_TIMEOUT_S = 5.0

# Number of insert-error rows to include in a log line before truncating.
ERR_SAMPLE = 3


@dataclass
class _Runtime:
    """Shared shutdown flag, keeps ruff PLW0603 happy without a `global`."""

    shutdown: bool = False


_runtime = _Runtime()


def _handle_signal(_signum: int, _frame: FrameType | None) -> None:
    """Flip the shutdown flag; the poll loop exits on its next tick."""
    _runtime.shutdown = True


def _to_row(msg_value: bytes) -> BronzeRow | None:
    """Decode a Kafka message payload into a bronze-table row, or None."""
    try:
        event: JsonObject = json.loads(msg_value)
    except json.JSONDecodeError:
        log.warning("skipping non-JSON message")
        return None

    actor = event.get("actor")
    repo = event.get("repo")

    def _s(v: JsonValue) -> str | None:
        return v if isinstance(v, str) else None

    return {
        "event_id": _s(event.get("id")),
        "event_type": _s(event.get("type")),
        "actor_login": _s(actor.get("login")) if isinstance(actor, dict) else None,
        "repo_name": _s(repo.get("name")) if isinstance(repo, dict) else None,
        "event_created_at": _s(event.get("created_at")),
        "ingested_at": datetime.now(UTC).isoformat(),
        "payload": json.dumps(event),
    }


def consume_and_load() -> None:
    """Run the main consume loop; batch-insert into BigQuery and commit offsets."""
    client = bigquery.Client(project=PROJECT)
    table_ref = f"{PROJECT}.{DATASET}.{TABLE}"

    consumer = Consumer(
        {
            "bootstrap.servers": BOOTSTRAP,
            "group.id": "bq-loader",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        },
    )
    consumer.subscribe([TOPIC])

    batch: list[BronzeRow] = []
    last_flush = datetime.now(UTC).timestamp()

    def flush() -> None:
        nonlocal batch, last_flush
        if not batch:
            return
        errors = client.insert_rows_json(table_ref, batch)
        if errors:
            # Streaming inserts return per-row errors; log and move on so we
            # don't stall the consumer. A production build should DLQ these.
            log.error("bq insert errors: %s", errors[:ERR_SAMPLE])
        else:
            log.info("inserted %d rows to %s", len(batch), table_ref)
        consumer.commit(asynchronous=False)
        batch = []
        last_flush = datetime.now(UTC).timestamp()

    try:
        while not _runtime.shutdown:
            msg = consumer.poll(1.0)
            if msg is None:
                if datetime.now(UTC).timestamp() - last_flush > BATCH_TIMEOUT_S:
                    flush()
                continue
            if msg.error():
                raise KafkaException(msg.error())

            row = _to_row(msg.value())
            if row:
                batch.append(row)

            if len(batch) >= BATCH_SIZE:
                flush()
    finally:
        flush()
        consumer.close()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    try:
        consume_and_load()
    except Exception:
        # Top-level crash barrier: log with traceback and exit non-zero so
        # a supervisor can restart.
        log.exception("consumer crashed")
        sys.exit(1)
