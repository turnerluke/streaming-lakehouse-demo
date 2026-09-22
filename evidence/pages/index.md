---
title: Streaming Lakehouse Demo
---

A **static snapshot** of the local DuckDB medallion. Data is a 30-row
hand-crafted seed representing four hours of GitHub-Events-style
activity across three repos. The full producer / consumer / Dagster
loop drives the same schema when pointed at real Kafka.

The whole warehouse rebuilds from seed on every push to `main`; see
the [source repository](https://github.com/turnerluke/streaming-lakehouse-demo)
for the pipeline behind it.

```sql overall
select * from local_duckdb.overall
```

<BigValue data={overall} value=total_events title="Events" />
<BigValue data={overall} value=unique_actors title="Actors" />
<BigValue data={overall} value=unique_repos title="Repos" />
<BigValue data={overall} value=event_types title="Event types" />

## Hourly activity

Every event bucketed to its hour and event type — the
`gold.fct_events_hourly` model.

```sql hourly
select * from local_duckdb.hourly
```

<BarChart
    data={hourly}
    x=event_hour
    y=event_count
    series=event_type
    type=stacked
    title="Events per hour by type"
/>

## Top repos

Total events per repo across the seeded window.

```sql top_repos
select * from local_duckdb.top_repos
```

<DataTable data={top_repos}>
    <Column id=repo_name title="Repo" />
    <Column id=events title="Events" contentType=colorscale />
    <Column id=unique_actors title="Actors" />
    <Column id=event_types title="Event types" />
</DataTable>

## Event-type breakdown

```sql event_types
select * from local_duckdb.event_types
```

<BarChart
    data={event_types}
    x=event_type
    y=events
    title="Events by type"
    swapXY=true
/>

## Repo attribute history (SCD Type 2)

Follow the seeded repos through their attribute changes on the
[Repos page](/repos).
