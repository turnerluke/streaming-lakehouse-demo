---
title: Repos & SCD Type 2 history
---

The `gold.dim_repo_scd2` model maintains one row per
`(repo, attribute-change window)`. Every event whose repo payload
differs on a tracked attribute (language, description, stargazers
count) closes the current row (`valid_to = new event time`,
`is_current = false`) and opens a new one.

## Current state

```sql current
select * from local_duckdb.repos_current
```

<DataTable data={current}>
    <Column id=repo_name title="Repo" />
    <Column id=repo_language title="Language" />
    <Column id=repo_description title="Description" wrap=true />
    <Column id=stargazers_count title="Stars" contentType=colorscale />
    <Column id=first_seen title="Current window opened" />
</DataTable>

## `octocat/hello-world` migration timeline

The seeded octocat repo goes through a Ruby → Python migration
across the four-hour window, plus incremental stargazer growth.
Each row is a distinct version.

```sql octocat_history
select * from local_duckdb.octocat_history
```

<DataTable data={octocat_history}>
    <Column id=valid_from title="Valid from" />
    <Column id=language title="Language" />
    <Column id=description title="Description" wrap=true />
    <Column id=stars title="Stars" contentType=colorscale />
    <Column id=flag title="" />
</DataTable>

## Versions per repo

```sql versions
select * from local_duckdb.versions_per_repo
```

<BarChart
    data={versions}
    x=repo_name
    y=version_count
    title="SCD2 versions per repo"
    swapXY=true
/>
