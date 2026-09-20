"""Dagster assets for the streaming half of the pipeline.

Two assets:
  * `github_events_published` — one poll of the GitHub Events API,
    unseen events pushed to Kafka.
  * `raw_events_ingested`     — one drain of Kafka into
    `local.bronze.raw_events` (DuckDB), downstream of the above.

Both are batch materializations that call the sprint-10 helper
functions (`publish_once` / `drain_to_duckdb`). Cross-materialization
dedup is Kafka's job (event ids as keys) and dbt's silver-layer
`qualify row_number()` clause.
"""

import os

from dagster import AssetExecutionContext, AssetKey, MaterializeResult, asset

from consumer.drain_to_duckdb import drain_to_duckdb
from producer.publish_once import publish_once


def _kafka_bootstrap() -> str:
    return os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")


def _topic() -> str:
    return os.environ.get("KAFKA_TOPIC_EVENTS", "github.events")


def _duckdb_path() -> str:
    return os.environ.get("DUCKDB_PATH", "dbt/target/local.duckdb")


@asset(
    group_name="streaming",
    description="One poll of the GitHub Events API; unseen events published to Kafka.",
)
def github_events_published(context: AssetExecutionContext) -> MaterializeResult:
    """Publish one page of GitHub events to Kafka."""
    seen: set[str] = set()
    token = os.environ.get("GITHUB_TOKEN") or None
    count = publish_once(
        bootstrap=_kafka_bootstrap(),
        topic=_topic(),
        seen=seen,
        token=token,
    )
    context.log.info("published %d new events to topic %s", count, _topic())
    return MaterializeResult(metadata={"events_published": count, "topic": _topic()})


@asset(
    # Match the dbt `bronze.raw_events` source key so downstream dbt
    # models see this materialization as their upstream. dbt-dagster
    # resolves the source's Dagster asset key from schema+name.
    key=AssetKey(["bronze", "raw_events"]),
    group_name="streaming",
    deps=[github_events_published],
    description="One drain of Kafka into `bronze.raw_events` (DuckDB).",
)
def raw_events_ingested(context: AssetExecutionContext) -> MaterializeResult:
    """Drain up to 100 events from Kafka into DuckDB bronze."""
    count = drain_to_duckdb(
        bootstrap=_kafka_bootstrap(),
        topic=_topic(),
        duckdb_path=_duckdb_path(),
    )
    context.log.info("ingested %d rows into bronze.raw_events at %s", count, _duckdb_path())
    return MaterializeResult(metadata={"rows_ingested": count, "duckdb_path": _duckdb_path()})
