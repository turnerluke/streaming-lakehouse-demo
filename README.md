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

## Quickstart (local)

```bash
cp .env.example .env
docker compose up -d          # Redpanda + Marquez
uv sync                       # or: pip install -e .
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

Repo standards (branch/PR rules, commit format, lint stack, sprint prompt
pattern, `typing.Any` ban) live in [`AGENTS.md`](AGENTS.md). Every
increment lands as a single focused PR driven by a `prompt-NN-<slug>.md`
at the repo root.

## Status

Scaffold. None of this is wired end-to-end yet — see `docs/TODO.md`.
Sprint 01 (`prompt-01-standards-alignment.md`) aligns the repo standards
with `cms-open-data`; subsequent sprints will pick up the pipeline work.
