# TODO

The scaffold is skeletal. To take it end-to-end:

## Local dev loop

- [ ] `uv sync` (or `pip install -e .[dev]`) and confirm imports.
- [ ] `docker compose up -d`; open Redpanda console at <http://localhost:8080>
      and Marquez at <http://localhost:3000>.
- [ ] Run producer + consumer against a local BQ emulator, or point at a real GCP project (see cloud loop).

## Cloud loop

- [ ] Create GCP project, link billing, **set $20 budget alert**.
- [ ] `cd terraform && cp terraform.tfvars.example terraform.tfvars` and fill in `project_id`.
- [ ] `terraform init && terraform apply`.
- [ ] Export `GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/../.secrets/sa-key.json`.
- [ ] `cd ../dbt && cp profiles.yml.example profiles.yml && dbt deps && dbt build`.
- [ ] Start producer + consumer; watch rows land in `bronze.raw_events`.

## Dagster

- [ ] `dagster dev -w dagster_project/workspace.yaml` to open the UI.
- [ ] Add an asset that wraps `producer/consumer` as a long-running sensor (currently only dbt is orchestrated).

## Lineage

- [ ] Install `openlineage-dbt`, invoke dbt as `dbt-ol build`, confirm events land in Marquez.

## Evidence

- [ ] `cd evidence && npm install && npm run sources && npm run dev`.
- [ ] Deploy to Cloudflare Pages or Netlify (both free).

## CI

- [ ] Enable Actions on the GitHub repo.
- [ ] Add a `dbt-cloud`-style job if you want scheduled cloud builds (optional).

## Stretch

- [ ] DLQ topic for consumer insert failures.
- [ ] Great Expectations or Soda checks on silver.
- [ ] Terraform-managed BigQuery scheduled queries as a fallback if Dagster is down.
