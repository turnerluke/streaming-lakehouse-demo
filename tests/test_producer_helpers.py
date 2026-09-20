"""Unit tests for `producer.github_events_producer` helpers."""

from __future__ import annotations

import time
from threading import Thread

from producer import github_events_producer as producer_mod
from producer.github_events_producer import (
    SEEN_CAP,
    SEEN_TRIM_TO,
    _publish_events,
    _sleep_responsively,
)
from tests.fakes import FakeKafkaProducer


def _event(event_id: str | int) -> dict[str, object]:
    """Minimal event shape — only the id matters for these tests."""
    return {"id": event_id, "type": "PushEvent"}


def test_publish_events_skips_seen_ids() -> None:
    """The same event id is only produced once."""
    fake = FakeKafkaProducer()

    first = _publish_events(fake, [_event("1"), _event("2"), _event("1")])
    second = _publish_events(fake, [_event("2"), _event("3")])

    assert first == 2
    assert second == 1
    assert [m.key for m in fake.messages] == [b"1", b"2", b"3"]


def test_publish_events_skips_non_string_ids() -> None:
    """Non-string ids never make it to the broker (and don't crash)."""
    fake = FakeKafkaProducer()

    count = _publish_events(fake, [_event(42), _event(None), _event("ok")])

    assert count == 1
    assert [m.key for m in fake.messages] == [b"ok"]


def test_publish_events_trims_seen_when_over_cap() -> None:
    """Dedup set trims once it exceeds SEEN_CAP."""
    fake = FakeKafkaProducer()

    events = [_event(str(i)) for i in range(SEEN_CAP + 5)]
    _publish_events(fake, events)

    assert len(producer_mod._runtime.seen) == SEEN_TRIM_TO  # noqa: SLF001


def test_sleep_responsively_bails_on_shutdown() -> None:
    """Setting the shutdown flag mid-sleep returns within ~1 second."""

    def flip_soon() -> None:
        time.sleep(0.1)
        producer_mod._runtime.shutdown = True  # noqa: SLF001

    Thread(target=flip_soon, daemon=True).start()

    start = time.monotonic()
    _sleep_responsively(30)
    elapsed = time.monotonic() - start

    # 30-second nominal sleep; must exit far sooner. Give generous headroom
    # for slow CI runners.
    assert elapsed < 3.0
