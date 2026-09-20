# Streaming Lakehouse Demo

A real-time data platform that ingests the public GitHub Events firehose into
BigQuery via Kafka, models it with dbt (Bronze / Silver / Gold), orchestrates
with Dagster, and publishes a live Evidence.dev dashboard. Lineage events are
emitted via OpenLineage.

## Architecture

```text
GitHub Events API
       |
       v
[producer] --> Redpanda (Kafka) --> [consumer] --> BigQuery bronze.raw_events
                                                          |
                                                          v
                                                    dbt (silver, gold)
                                                          |
                                                          v
                                                    Evidence dashboard
       ^                                                  ^
       |                                                  |
       +-------- Dagster (assets + schedules) ------------+
                          |
                          v
                    Marquez (OpenLineage)
```

## Layout

| Path                 | What lives here                                                               |
| -------------------- | ----------------------------------------------------------------------------- |
| `producer/`          | Polls GitHub Events API, publishes JSON to a Kafka topic                      |
| `consumer/`          | Reads the Kafka topic, streams inserts into `bronze.raw_events`               |
| `dbt/`               | dbt project with bronze sources, silver staging, gold dims/facts (incl. SCD2) |
| `dagster_project/`   | Dagster assets wrapping producer/consumer/dbt; OpenLineage integration        |
| `terraform/`         | GCP project bootstrap: BigQuery datasets, service account, IAM                |
| `evidence/`          | Evidence.dev site for the public dashboard                                    |
| `.github/workflows/` | CI: dbt compile, `sqlfluff`, dbt tests                                        |
| `scripts/`           | One-off helpers (setup, billing alert reminder)                               |

## Cost expectation

Designed to sit at **$0/mo** on the BigQuery free tier (1 TB queries + 10 GB
storage/month). See `docs/cost.md` before running anything in the cloud.

**Set a $20 billing alert on the GCP project before your first `terraform apply`.**
`scripts/set-billing-alert.sh` is a reminder — the console click is faster.

## Local demo (zero cloud, ~30 seconds)

The dbt project ships with a 30-row seed dataset and a DuckDB target,
so you can build the whole warehouse locally without provisioning
anything:

```bash
uv sync
cd dbt
cp profiles.yml.example profiles.yml
uv run dbt deps                       # fetch dbt-utils
uv run dbt seed --target duckdb
uv run dbt build --target duckdb
```

That produces `dbt/target/local.duckdb` with populated silver +
gold tables. Poke at it:

```python
# in the dbt/ dir:
import duckdb

conn = duckdb.connect("target/local.duckdb", read_only=True)
conn.sql("select * from gold.dim_repo_scd2 limit 5").show()
```

## Quickstart (streaming, local)

```bash
cp .env.example .env
docker compose up -d          # Redpanda + Marquez
uv sync
python -m producer.github_events_producer   # in one terminal
python -m consumer.bq_streaming_loader      # in another
```

## Quickstart (cloud)

1. `gcloud auth application-default login`
2. `cd terraform && terraform init && terraform apply`
3. Export the emitted service-account key path as `GOOGLE_APPLICATION_CREDENTIALS`
4. `cd dbt && dbt build`
5. `cd evidence && npm install && npm run sources && npm run dev`

## Contributing / conventions

Repo standards (branch/PR rules, commit format, lint stack, sprint
discipline, `typing.Any` ban) live in [`AGENTS.md`](AGENTS.md). Every
increment lands as a single focused PR driven by a local (gitignored)
`prompt-<slug>.md` at the repo root.

## Status

Local dbt build works end-to-end against DuckDB. Streaming path
(producer -> Kafka -> consumer -> warehouse) is code-complete with
unit tests; wiring the local integration test and the Dagster asset
graph are the next sprints. Cloud (real BigQuery + a live Evidence
dashboard) is deliberately deferred.
