"""Docker-backed fixtures for the integration test suite.

A session-scoped Redpanda container is spun up once per pytest session,
which keeps the "first pull is slow" cost off every test.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Iterator


# testcontainers spawns a "ryuk" sidecar that mounts the host docker
# socket to clean up orphaned containers. That mount doesn't work on
# Colima (host-side socket path is not passthroughable into the VM),
# so we disable ryuk before importing anything from testcontainers.
# The `with` context managers below still stop containers on teardown;
# the only thing lost is cleanup after a hard crash of the pytest
# process, which is acceptable for a demo repo.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

from testcontainers.community.kafka import RedpandaContainer


@pytest.fixture(scope="session")
def redpanda_bootstrap() -> Iterator[str]:
    """Yield the bootstrap-server string for a running Redpanda container."""
    with RedpandaContainer() as container:
        yield container.get_bootstrap_server()
