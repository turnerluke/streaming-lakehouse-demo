"""Dagster definitions: dbt asset graph + scheduled job.

Note: `Iterator` is a runtime import (not `TYPE_CHECKING`) and this
module deliberately omits `from __future__ import annotations`.
Dagster's `@asset` and `@dbt_assets` decorators inspect return-type
annotations at import time; stringified annotations (from
`__future__ import annotations` or TYPE_CHECKING imports) trip a
`DagsterInvalidDefinitionError` because Dagster can't resolve the
name in a local scope.
"""

from collections.abc import Iterator
from pathlib import Path

from dagster import AssetExecutionContext, AssetSelection, Definitions, ScheduleDefinition, define_asset_job
from dagster_dbt import DbtCliResource, dbt_assets

from dagster_project.streaming_assets import github_events_published, raw_events_ingested


DBT_PROJECT_DIR = Path(__file__).parent.parent / "dbt"
DBT_PROFILES_DIR = DBT_PROJECT_DIR

dbt_resource = DbtCliResource(project_dir=str(DBT_PROJECT_DIR), profiles_dir=str(DBT_PROFILES_DIR))

# Manifest is generated on first `dbt parse`. Kept out of the tree until then.
MANIFEST_PATH = DBT_PROJECT_DIR / "target" / "manifest.json"


@dbt_assets(
    manifest=MANIFEST_PATH,
    # Seeds are static local demo data (sprint 08's `raw_events.csv`) and
    # share their asset key with the bronze source; excluding them here
    # avoids the duplicate-key error and reflects that seeding is a
    # one-time manual step, not orchestration surface.
    exclude="resource_type:seed",
)
def project_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource) -> Iterator[object]:
    """Dbt build streamed as Dagster asset events."""
    yield from dbt.cli(["build", "--exclude", "resource_type:seed"], context=context).stream()


dbt_hourly_job = define_asset_job(
    name="dbt_hourly_job",
    # Scope explicitly to dbt-emitted assets. `AssetSelection.all()`
    # would pull the streaming assets into the schedule too, which
    # would hit GitHub Events + Kafka every hour — not what we want
    # for an unattended cron.
    selection=AssetSelection.assets(project_dbt_assets),
)

hourly_schedule = ScheduleDefinition(
    job=dbt_hourly_job,
    cron_schedule="5 * * * *",
)


defs = Definitions(
    assets=[
        github_events_published,
        raw_events_ingested,
        project_dbt_assets,
    ],
    resources={"dbt": dbt_resource},
    jobs=[dbt_hourly_job],
    schedules=[hourly_schedule],
)
