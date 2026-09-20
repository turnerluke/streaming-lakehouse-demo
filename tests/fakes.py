"""Test doubles for the streaming pipeline.

`FakeKafkaProducer` records `.produce()` calls; `FakeKafkaConsumer`
serves a scripted list of messages so drain-loop tests don't need
Docker.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProducedMessage:
    """A single call to `FakeKafkaProducer.produce()`."""

    topic: str
    key: bytes
    value: bytes


@dataclass
class FakeKafkaProducer:
    """Duck-typed stand-in for `confluent_kafka.Producer`."""

    messages: list[ProducedMessage] = field(default_factory=list)

    def produce(
        self,
        topic: str,
        key: bytes,
        value: bytes,
        on_delivery: object = None,
    ) -> None:
        """Record a message; do not send it anywhere."""
        self.messages.append(ProducedMessage(topic=topic, key=key, value=value))

    def poll(self, _timeout: float) -> None:
        """Real Producer.poll dispatches delivery callbacks — no-op here."""

    def flush(self, _timeout: float = 10.0) -> int:
        """Real Producer.flush blocks until buffer drains — no-op here."""
        return 0


class _FakeMessage:
    """Duck-typed stand-in for a confluent_kafka `Message`."""

    def __init__(self, value: bytes) -> None:
        self._value = value

    def value(self) -> bytes:
        """Message payload bytes."""
        return self._value

    def error(self) -> None:
        """No-error message — real Message returns a KafkaError or None."""
        return


@dataclass
class FakeKafkaConsumer:
    """Duck-typed stand-in for `confluent_kafka.Consumer`.

    Yields the scripted `messages` in order, then returns None forever.
    """

    messages: list[bytes] = field(default_factory=list)
    subscribed_topics: list[str] = field(default_factory=list)
    committed: bool = False
    closed: bool = False

    def subscribe(self, topics: list[str]) -> None:
        """Record the subscribed topics; no rebalance to simulate."""
        self.subscribed_topics = list(topics)

    def poll(self, _timeout: float) -> _FakeMessage | None:
        """Pop the next scripted message, or return None once drained."""
        if not self.messages:
            return None
        return _FakeMessage(self.messages.pop(0))

    def commit(self, *, asynchronous: bool = True) -> None:
        """Record that a commit happened."""
        self.committed = True

    def close(self) -> None:
        """Record that the consumer was closed."""
        self.closed = True
