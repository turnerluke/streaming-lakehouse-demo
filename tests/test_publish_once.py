"""Unit tests for `producer.publish_once` using a FakeKafkaProducer."""

from __future__ import annotations

from http import HTTPStatus
import json
from typing import TYPE_CHECKING
from unittest.mock import patch

from producer import publish_once as publish_once_mod

from tests.fakes import FakeKafkaProducer


if TYPE_CHECKING:
    import pytest


class _FakeResponse:
    def __init__(self, status: int, body: object = None) -> None:
        self.status_code = status
        self._body = body
        self.text = "" if body is None else str(body)

    def json(self) -> object:
        return self._body


def _mock_producer(fake: FakeKafkaProducer) -> object:
    return patch.object(publish_once_mod, "Producer", return_value=fake)


def test_publish_once_publishes_unseen_events() -> None:
    """A 200 with 3 events -> 3 kafka publishes; seen set updated."""
    fake = FakeKafkaProducer()
    seen: set[str] = set()
    events = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    resp = _FakeResponse(HTTPStatus.OK, events)

    with (
        _mock_producer(fake),
        patch.object(publish_once_mod.requests, "get", return_value=resp),
    ):
        count = publish_once_mod.publish_once("localhost:9092", "topic", seen)

    assert count == 3
    assert seen == {"a", "b", "c"}
    assert [m.key for m in fake.messages] == [b"a", b"b", b"c"]
    payloads = [json.loads(m.value) for m in fake.messages]
    assert payloads == events


def test_publish_once_skips_seen_events() -> None:
    """Events already in `seen` are not re-published."""
    fake = FakeKafkaProducer()
    seen = {"a"}
    events = [{"id": "a"}, {"id": "b"}]
    resp = _FakeResponse(HTTPStatus.OK, events)

    with (
        _mock_producer(fake),
        patch.object(publish_once_mod.requests, "get", return_value=resp),
    ):
        count = publish_once_mod.publish_once("localhost:9092", "topic", seen)

    assert count == 1
    assert [m.key for m in fake.messages] == [b"b"]


def test_publish_once_304_returns_zero_and_leaves_seen_alone() -> None:
    """A 304 Not Modified means 'no new events'; publish_once returns 0."""
    fake = FakeKafkaProducer()
    seen: set[str] = set()
    resp = _FakeResponse(HTTPStatus.NOT_MODIFIED)

    with (
        _mock_producer(fake),
        patch.object(publish_once_mod.requests, "get", return_value=resp),
    ):
        count = publish_once_mod.publish_once("localhost:9092", "topic", seen)

    assert count == 0
    assert fake.messages == []
    assert seen == set()


def test_publish_once_swallows_request_exception() -> None:
    """Network errors are logged, not raised — Dagster asset stays green."""
    fake = FakeKafkaProducer()
    seen: set[str] = set()

    def _raise(*_a: object, **_k: object) -> None:
        msg = "dns"
        raise publish_once_mod.requests.ConnectionError(msg)

    with (
        _mock_producer(fake),
        patch.object(publish_once_mod.requests, "get", side_effect=_raise),
    ):
        count = publish_once_mod.publish_once("localhost:9092", "topic", seen)

    assert count == 0
    assert fake.messages == []


def test_publish_once_ignores_non_string_ids(caplog: pytest.LogCaptureFixture) -> None:
    """Events with integer or missing ids are silently skipped."""
    fake = FakeKafkaProducer()
    seen: set[str] = set()
    events = [{"id": 42}, {"id": None}, {"id": "good"}]
    resp = _FakeResponse(HTTPStatus.OK, events)

    with (
        _mock_producer(fake),
        patch.object(publish_once_mod.requests, "get", return_value=resp),
    ):
        count = publish_once_mod.publish_once("localhost:9092", "topic", seen)

    assert count == 1
    assert [m.key for m in fake.messages] == [b"good"]
