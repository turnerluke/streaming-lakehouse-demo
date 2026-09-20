"""Poll the public GitHub Events firehose and publish each event to Kafka.

Respects the ETag / X-Poll-Interval headers GitHub returns so we don't burn
rate limit. Idempotency is best-effort via event id as the Kafka key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from http import HTTPStatus
import json
import logging
import os
import signal
import sys
import time
from typing import TYPE_CHECKING

from confluent_kafka import Producer
from dotenv import load_dotenv
import requests


if TYPE_CHECKING:
    from types import FrameType

    from confluent_kafka import KafkaError, Message


load_dotenv()

log = logging.getLogger("producer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

GITHUB_URL = "https://api.github.com/events"
BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
TOPIC = os.environ.get("KAFKA_TOPIC_EVENTS", "github.events")
TOKEN = os.environ.get("GITHUB_TOKEN") or None

# Dedup cap: keep at most SEEN_CAP recent event ids in memory so the set
# doesn't grow unbounded during a long run. When we hit the cap, drop the
# oldest half — the poll interval is short enough that older ids will not
# reappear.
SEEN_CAP = 10_000
SEEN_TRIM_TO = 5_000

# Number of most-recent characters of an error body to include in log lines.
ERR_BODY_CHARS = 200


@dataclass
class _Runtime:
    """Mutable state shared by the poll loop and signal handlers.

    Using a dataclass instead of module-level `global` variables lets ruff's
    strictest ruleset stay happy without disabling PLW0603.
    """

    shutdown: bool = False
    etag: str | None = None
    poll_interval: int = 60
    seen: set[str] = field(default_factory=set)


_runtime = _Runtime()


def _handle_signal(_signum: int, _frame: FrameType | None) -> None:
    """Flip the shared shutdown flag; the poll loop exits on its next tick."""
    _runtime.shutdown = True


def _delivery(err: KafkaError | None, _msg: Message) -> None:
    """confluent_kafka delivery callback — log-only, never raises."""
    if err is not None:
        log.warning("kafka delivery failed: %s", err)


def _publish_events(producer: Producer, events: list[dict[str, object]]) -> int:
    """Publish only unseen events; update the shared dedup set. Returns new count."""
    seen = _runtime.seen
    new_count = 0
    for event in events:
        event_id = event.get("id")
        if not isinstance(event_id, str) or event_id in seen:
            continue
        seen.add(event_id)
        producer.produce(
            TOPIC,
            key=event_id.encode(),
            value=json.dumps(event).encode(),
            on_delivery=_delivery,
        )
        new_count += 1

    if len(seen) > SEEN_CAP:
        _runtime.seen = set(list(seen)[-SEEN_TRIM_TO:])
    return new_count


def _sleep_responsively(seconds: int) -> None:
    """Sleep in 1s slices so a shutdown signal is picked up quickly."""
    for _ in range(seconds):
        if _runtime.shutdown:
            return
        time.sleep(1)


def poll_and_publish() -> None:
    """Run the main poll loop; publish new events to Kafka respecting rate limits."""
    producer = Producer({"bootstrap.servers": BOOTSTRAP, "linger.ms": 50})
    headers = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    while not _runtime.shutdown:
        req_headers = dict(headers)
        if _runtime.etag:
            req_headers["If-None-Match"] = _runtime.etag

        try:
            resp = requests.get(GITHUB_URL, headers=req_headers, timeout=15)
        except requests.RequestException as exc:
            log.warning("github request failed: %s", exc)
            _sleep_responsively(_runtime.poll_interval)
            continue

        _runtime.poll_interval = int(resp.headers.get("X-Poll-Interval", _runtime.poll_interval))

        if resp.status_code == HTTPStatus.NOT_MODIFIED:
            log.debug("no new events (304)")
        elif resp.status_code == HTTPStatus.OK:
            _runtime.etag = resp.headers.get("ETag") or _runtime.etag
            new_count = _publish_events(producer, resp.json())
            producer.poll(0)
            log.info("published %d new events (poll interval %ds)", new_count, _runtime.poll_interval)
        else:
            log.warning("github returned %s: %s", resp.status_code, resp.text[:ERR_BODY_CHARS])

        _sleep_responsively(_runtime.poll_interval)

    log.info("flushing producer...")
    producer.flush(10)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    try:
        poll_and_publish()
    except Exception:
        # Top-level crash barrier: log with traceback and exit non-zero so
        # a supervisor can restart. Narrower excepts happen inside the loop.
        log.exception("producer crashed")
        sys.exit(1)
