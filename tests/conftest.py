"""Shared pytest fixtures.

- Sets env vars the pipeline modules read at import-time BEFORE those
  modules get imported below.
- Resets the shared `_runtime` state on producer/consumer between tests
  so state can't leak (dedup set, shutdown flag).
"""

from __future__ import annotations

import os


# Producer/consumer read these at import time. Set them BEFORE the imports
# below, or those imports will explode on `os.environ[...]`.
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("BQ_DATASET_BRONZE", "bronze")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
os.environ.setdefault("KAFKA_TOPIC_EVENTS", "github.events.test")

from consumer import bq_streaming_loader as consumer_mod
from producer import github_events_producer as producer_mod

import pytest


@pytest.fixture(autouse=True)
def _reset_pipeline_runtimes() -> None:
    """Clear shared shutdown/dedup state before each test."""
    producer_mod._runtime.shutdown = False
    producer_mod._runtime.etag = None
    producer_mod._runtime.poll_interval = 60
    producer_mod._runtime.seen = set()
    consumer_mod._runtime.shutdown = False
