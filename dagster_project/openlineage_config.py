"""OpenLineage wiring for dbt runs invoked through Dagster.

Enable by setting these env vars before starting Dagster:

    OPENLINEAGE_URL=http://localhost:5000
    OPENLINEAGE_NAMESPACE=streaming-lakehouse
    DBT_OPENLINEAGE_ENABLED=1

Dagster's dbt integration will pick up the `openlineage-dbt` wrapper if
`dbt-ol` is on PATH; alternatively call the dbt CLI as `dbt-ol build`.
See https://openlineage.io/docs/integrations/dbt for the latest guidance.
"""
