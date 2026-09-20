{{ config(
    materialized='incremental',
    partition_by={'field': 'event_hour', 'data_type': 'timestamp', 'granularity': 'day'},
    cluster_by=['event_type'],
    incremental_strategy='insert_overwrite'
) }}

with events as (
    select *
    from {{ ref('stg_github_events') }}
    {% if is_incremental() %}
        where
            event_created_at
            >= timestamp_sub(current_timestamp(), interval 3 hour)
    {% endif %}
)

select
    timestamp_trunc(event_created_at, hour) as event_hour,
    event_type,
    count(*) as event_count,
    count(distinct actor_login) as unique_actors,
    count(distinct repo_name) as unique_repos
from events
group by 1, 2
