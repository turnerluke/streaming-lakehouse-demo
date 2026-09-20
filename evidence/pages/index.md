---
title: GitHub Events — Live
---

Real-time view of the public GitHub Events firehose, ingested via Kafka into
BigQuery and modeled with dbt.

```sql events_last_24h
select
    event_hour,
    event_type,
    event_count
from bigquery.gold.fct_events_hourly
where event_hour >= timestamp_sub(current_timestamp(), interval 24 hour)
order by event_hour
```

<LineChart data={events_last_24h} x=event_hour y=event_count series=event_type />

```sql top_repos
select repo_name, count(*) as events
from bigquery.silver.stg_github_events
where event_created_at >= timestamp_sub(current_timestamp(), interval 1 hour)
group by 1
order by events desc
limit 20
```

<DataTable data={top_repos} />
