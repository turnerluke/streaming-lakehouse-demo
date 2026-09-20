"""Shared pytest fixtures.

- Ensures env vars the pipeline modules read at import-time are set
  before those modules are imported.
- Resets the shared `_runtime` state on producer/consumer between tests
  so state can't leak (dedup set, shutdown flag).
"""

from __future__ import annotations

import os

import pytest


# Producer/consumer read these at import time. Set them once for the whole
# suite before any test module imports the pipeline code.
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("BQ_DATASET_BRONZE", "bronze")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
os.environ.setdefault("KAFKA_TOPIC_EVENTS", "github.events.test")


@pytest.fixture(autouse=True)
def _reset_pipeline_runtimes() -> None:
    """Clear shared shutdown/dedup state before each test."""
    # Imported lazily so tests that don't touch the pipeline don't pay the cost.
    from consumer import bq_streaming_loader as consumer_mod
    from producer import github_events_producer as producer_mod

    producer_mod._runtime.shutdown = False  # noqa: SLF001
    producer_mod._runtime.etag = None  # noqa: SLF001
    producer_mod._runtime.poll_interval = 60  # noqa: SLF001
    producer_mod._runtime.seen = set()  # noqa: SLF001
    consumer_mod._runtime.shutdown = False  # noqa: SLF001
