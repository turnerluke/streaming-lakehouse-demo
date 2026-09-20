"""Test doubles for the streaming pipeline.

`FakeKafkaProducer` records `.produce()` calls so assertions can inspect
what the producer would have shipped without needing a live broker.
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
        on_delivery: object = None,  # noqa: ARG002 (matches real signature)
    ) -> None:
        """Record a message; do not send it anywhere."""
        self.messages.append(ProducedMessage(topic=topic, key=key, value=value))

    def poll(self, _timeout: float) -> None:
        """Real Producer.poll dispatches delivery callbacks — no-op here."""
