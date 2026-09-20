"""Dagster definitions: dbt asset graph + scheduled job."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from dagster import AssetExecutionContext, AssetSelection, Definitions, ScheduleDefinition, define_asset_job
from dagster_dbt import DbtCliResource, dbt_assets


if TYPE_CHECKING:
    from collections.abc import Iterator


DBT_PROJECT_DIR = Path(__file__).parent.parent / "dbt"
DBT_PROFILES_DIR = DBT_PROJECT_DIR

dbt_resource = DbtCliResource(project_dir=str(DBT_PROJECT_DIR), profiles_dir=str(DBT_PROFILES_DIR))

# Manifest is generated on first `dbt parse`. Kept out of the tree until then.
MANIFEST_PATH = DBT_PROJECT_DIR / "target" / "manifest.json"


@dbt_assets(manifest=MANIFEST_PATH)
def project_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource) -> Iterator[object]:
    """Dbt build streamed as Dagster asset events."""
    yield from dbt.cli(["build"], context=context).stream()


dbt_hourly_job = define_asset_job(
    name="dbt_hourly_job",
    selection=AssetSelection.all(),
)

hourly_schedule = ScheduleDefinition(
    job=dbt_hourly_job,
    cron_schedule="5 * * * *",
)


defs = Definitions(
    assets=[project_dbt_assets],
    resources={"dbt": dbt_resource},
    jobs=[dbt_hourly_job],
    schedules=[hourly_schedule],
)
