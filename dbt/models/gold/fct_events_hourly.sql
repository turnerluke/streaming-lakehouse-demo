{% set partition = (
    {'field': 'event_hour', 'data_type': 'timestamp', 'granularity': 'day'}
    if target.type == 'bigquery' else none
) %}
{% set cluster = ['event_type'] if target.type == 'bigquery' else none %}

{{ config(
    materialized='incremental',
    partition_by=partition,
    cluster_by=cluster,
    incremental_strategy='insert_overwrite'
) }}

with events as (
    select *
    from {{ ref('stg_github_events') }}
    {% if is_incremental() %}
        where event_created_at >= {{ hours_ago(3) }}
    {% endif %}
)

select
    {{ trunc_hour('event_created_at') }} as event_hour,
    event_type,
    count(*) as event_count,
    count(distinct actor_login) as unique_actors,
    count(distinct repo_name) as unique_repos
from events
group by 1, 2
