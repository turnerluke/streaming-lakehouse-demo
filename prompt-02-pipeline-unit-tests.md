# Prompt: Sprint 02 — Unit tests for the producer and consumer helpers

## Why now

Sprint 01 hardened repo standards but left the pipeline code (producer /
consumer) exercised by nothing more than `ruff`. The transformation
helpers — `_to_row`, `_publish_events`, and the message-decoding path —
have real behavior worth pinning down before we point them at cloud
infra: null-handling on missing `actor` / `repo` blobs, dedup semantics
when GitHub replays an event id inside the same poll window, batch
overflow when the dedup cap is hit.

Deferring these to "we'll test it live" almost always means we don't.

Depends on `chore/repo-standards-alignment` (sprint 01) being merged.

## Goal

`tests/test_producer_helpers.py` and `tests/test_consumer_helpers.py`
each land a focused suite that exercises the pure functions in
`producer/github_events_producer.py` and
`consumer/bq_streaming_loader.py`. No docker, no network, no cloud —
these are unit tests, not integration tests (that's a future sprint).

Coverage bar: every non-`__main__` function in those two modules gets
at least one direct test; every branch in `_to_row` and
`_publish_events` gets an assertion.

## Approach

Single `test:` PR. Branch from `main`:

```bash
git checkout main && git pull --ff-only   # (locally: git fetch origin main)
git checkout -b test/pipeline-unit-tests
```

1. Add `tests/test_consumer_helpers.py`:
    - `test_to_row_extracts_flat_fields` — happy path with a full event.
    - `test_to_row_returns_none_on_bad_json` — malformed bytes.
    - `test_to_row_tolerates_missing_actor_and_repo` — the two `or {}`
      branches from the original impl are now proper `isinstance`
      guards; make sure they still return `None` for those columns
      without raising.
    - `test_to_row_ignores_non_string_ids` — GitHub occasionally returns
      integer-typed values in edge cases; the `_s()` helper must drop
      them without crashing.
2. Add `tests/test_producer_helpers.py`:
    - `test_publish_events_skips_seen_ids` — feed the same event twice,
      assert only one `produce` call.
    - `test_publish_events_skips_non_string_ids` — same input as
      consumer test #4 but for the producer's dedup path.
    - `test_publish_events_trims_seen_when_over_cap` — inject
      `SEEN_CAP + 1` fake ids and assert the shared set is trimmed to
      `SEEN_TRIM_TO` afterwards.
    - `test_sleep_responsively_bails_on_shutdown` — set the shared
      shutdown flag mid-sleep, assert we return promptly.
3. Use a `FakeProducer` (a stub with a `.produce()` that records call
   args) rather than mocking `confluent_kafka.Producer` itself — the
   mocks-vs-fakes tradeoff is real and the fake is nicer to read.
4. Reset `_runtime` between tests via a `conftest.py` autouse fixture
   so state doesn't leak.
5. Enable ruff's per-file relaxations on tests (already configured in
   `ruff.toml`); no test-side ignores needed beyond that.

## Files

|     | Path                                                                         |
| --- | ---------------------------------------------------------------------------- |
| ADD | `tests/conftest.py` (autouse fixture that resets producer/consumer runtimes) |
| ADD | `tests/test_producer_helpers.py`                                             |
| ADD | `tests/test_consumer_helpers.py`                                             |
| ADD | `tests/fakes.py` (`FakeKafkaProducer`, minimal fake)                         |

## Verification

```bash
uv run pytest tests/ --cov=producer --cov=consumer --cov-report=term-missing
uv run pre-commit run --all-files
```

- Expect > 90% branch coverage on the two target modules.
- `_to_row` and `_publish_events` show no missing lines.
- Existing 9 repo-standards tests still pass.
- Pre-commit clean.

Paste the coverage summary into the PR description.

## Out of scope

- Integration test with a real Redpanda container (Sprint 03 candidate).
- Consumer batch/flush loop coverage — that path needs a running Kafka
  broker to exercise honestly and is better as an integration test.
- Any change to `producer/consumer` production code beyond what's
  strictly required to make it testable (e.g. exposing `_runtime` as a
  module attribute — already done).
- dbt tests, Terraform tests, Dagster asset tests.

## Gotchas

- `producer/github_events_producer.py` has module-level side effects on
  import: `load_dotenv()`, `logging.basicConfig()`, reading env vars.
  Tests must not depend on any specific env-var state — use fresh
  fixture data, don't touch `os.environ`.
- `consumer/bq_streaming_loader.py` reads `os.environ["GCP_PROJECT_ID"]`
  at import time. The test suite must set this before importing:
  either in `conftest.py` via `monkeypatch.setenv` at module scope, or
  by making the assignment lazy. Prefer the former — moving the read
  is out of scope for this sprint.
- `interrogate` requires docstrings on every non-private test helper.
  The `FakeKafkaProducer` class in `tests/fakes.py` will need one.
- Ruff's `S101` (assert-used) is already ignored for `**/tests/**.py`
  per `ruff.toml` per-file-ignores, so `assert x == y` is fine.
