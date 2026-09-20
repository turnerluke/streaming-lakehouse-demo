"""Drain Kafka -> DuckDB for one Dagster materialization cycle.

Analogous to `bq_streaming_loader.consume_and_load` but writes to a local
DuckDB file instead of BigQuery. The BQ path stays for the cloud story;
this one is what the Dagster streaming asset uses in local dev.
"""

from __future__ import annotations

import logging
from pathlib import Path

from confluent_kafka import Consumer, KafkaException
import duckdb

from consumer.bq_streaming_loader import _to_row


log = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
create schema if not exists bronze;

create table if not exists bronze.raw_events (
    event_id varchar,
    event_type varchar,
    actor_login varchar,
    repo_name varchar,
    event_created_at timestamp,
    ingested_at timestamp,
    payload varchar
);
"""


def drain_to_duckdb(
    bootstrap: str,
    topic: str,
    duckdb_path: str,
    max_messages: int = 100,
    poll_timeout_s: float = 5.0,
) -> int:
    """Read up to `max_messages` from Kafka, decode, insert into DuckDB.

    Args:
        bootstrap: Kafka bootstrap-servers.
        topic: Kafka topic to consume.
        duckdb_path: Filesystem path of the DuckDB file. Created if missing.
        max_messages: Cap on messages drained in this call.
        poll_timeout_s: How long a single `consumer.poll()` waits before
            returning None on an empty topic. Total wall-clock for the
            call is at most ~`poll_timeout_s` after the last message.

    Returns:
        Number of rows inserted. Zero if the topic was empty for the
        whole poll window.

    """
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": "dagster-drain-to-duckdb",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        },
    )
    consumer.subscribe([topic])

    rows: list[tuple[str | None, ...]] = []
    try:
        while len(rows) < max_messages:
            msg = consumer.poll(poll_timeout_s)
            if msg is None:
                break
            if msg.error():
                raise KafkaException(msg.error())
            row = _to_row(msg.value())
            if row is None:
                continue
            rows.append(
                (
                    row["event_id"],
                    row["event_type"],
                    row["actor_login"],
                    row["repo_name"],
                    row["event_created_at"],
                    row["ingested_at"],
                    row["payload"],
                ),
            )
        if rows:
            # Ensure the parent dir exists — on a fresh clone, `dbt/target/`
            # doesn't yet, and `duckdb.connect` raises IOException rather
            # than creating it.
            Path(duckdb_path).parent.mkdir(parents=True, exist_ok=True)
            conn = duckdb.connect(duckdb_path)
            try:
                conn.execute(_CREATE_TABLE_SQL)
                conn.executemany(
                    "insert into bronze.raw_events values (?, ?, ?, ?, ?, ?, ?)",
                    rows,
                )
            finally:
                conn.close()
            consumer.commit(asynchronous=False)
            log.info("inserted %d rows into %s:bronze.raw_events", len(rows), duckdb_path)
    finally:
        consumer.close()
    return len(rows)
