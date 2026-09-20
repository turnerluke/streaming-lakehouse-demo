"""One-shot poll of GitHub Events -> Kafka, extracted from the long-running loop.

Used by Dagster's streaming asset (`github_events_published`) to run a
single materialization cycle. The long-running `poll_and_publish` in
`github_events_producer.py` still exists for standalone use.
"""

from __future__ import annotations

from http import HTTPStatus
import json
import logging
from typing import TYPE_CHECKING

from confluent_kafka import Producer
import requests


if TYPE_CHECKING:
    from confluent_kafka import KafkaError, Message

log = logging.getLogger(__name__)

GITHUB_URL = "https://api.github.com/events"

# Max bytes of a non-200 response body to include in a log line before truncating.
ERR_BODY_CHARS = 200


def _noop_delivery(err: KafkaError | None, _msg: Message) -> None:
    """Log-only delivery callback."""
    if err is not None:
        log.warning("kafka delivery failed: %s", err)


def publish_once(
    bootstrap: str,
    topic: str,
    seen: set[str],
    token: str | None = None,
    timeout_s: float = 15.0,
) -> int:
    """Fetch one page of GitHub Events and publish unseen ones to Kafka.

    Args:
        bootstrap: Kafka bootstrap-servers connection string.
        topic: Kafka topic to publish to.
        seen: Mutable set of event ids already published (dedup guard).
            The Dagster asset scopes this per-materialization (fresh
            set each call) so a whole page of events is treated as new;
            cross-call dedup is left to Kafka's event-id-keyed
            compaction and dbt silver's `qualify row_number()`. A
            caller who wants cross-poll dedup can pass a long-lived
            set — nothing prevents it.
        token: Optional GitHub personal access token (raises rate limit
            from 60 to 5000 req/hr).
        timeout_s: HTTP timeout for the GitHub request.

    Returns:
        Number of new events published this call. Zero on 304 (no new
        events since last ETag) or on request failure — errors are logged,
        not raised, so a Dagster asset materialization doesn't fail hard
        on a transient upstream hiccup.

    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(GITHUB_URL, headers=headers, timeout=timeout_s)
    except requests.RequestException as exc:
        log.warning("github request failed: %s", exc)
        return 0

    if resp.status_code == HTTPStatus.NOT_MODIFIED:
        return 0
    if resp.status_code != HTTPStatus.OK:
        log.warning("github returned %s: %s", resp.status_code, resp.text[:ERR_BODY_CHARS])
        return 0

    events = resp.json()
    producer = Producer({"bootstrap.servers": bootstrap, "linger.ms": 50})

    new_count = 0
    for event in events:
        event_id = event.get("id")
        if not isinstance(event_id, str) or event_id in seen:
            continue
        seen.add(event_id)
        producer.produce(
            topic,
            key=event_id.encode(),
            value=json.dumps(event).encode(),
            on_delivery=_noop_delivery,
        )
        new_count += 1

    producer.flush(10)
    return new_count
