{{ config(
    materialized='incremental',
    unique_key='repo_version_key',
    on_schema_change='append_new_columns'
) }}

-- Slowly Changing Dimension Type 2 for GitHub repos.
--
-- We derive repo attributes from each event's payload snapshot. When any
-- tracked attribute changes we close the current row (valid_to = new event
-- time, is_current = false) and open a new one. This is a demo-grade SCD2
-- built entirely with dbt + BigQuery merge semantics.

with events as (
    select
        repo_name,
        event_created_at,
        json_value(payload, '$.repo.id') as repo_id,
        json_value(payload, '$.payload.repository.language') as repo_language,
        json_value(payload, '$.payload.repository.description')
            as repo_description,
        cast(
            json_value(payload, '$.payload.repository.stargazers_count')
            as int64
        ) as stargazers_count
    from {{ ref('stg_github_events') }}
    where
        repo_name is not null
        {% if is_incremental() %}
            and event_created_at > (
                select coalesce(max(t.valid_from), timestamp('1970-01-01'))
                from {{ this }} as t
            )
        {% endif %}
),

-- Only keep rows where an attribute changed vs. the prior event per repo.
changes as (
    select
        repo_name,
        repo_id,
        repo_language,
        repo_description,
        stargazers_count,
        event_created_at as valid_from,
        lag(repo_language) over w as prev_repo_language,
        lag(repo_description) over w as prev_repo_description,
        lag(stargazers_count) over w as prev_stargazers_count
    from events
    window w as (partition by repo_name order by event_created_at)
),

filtered as (
    select
        repo_name,
        repo_id,
        repo_language,
        repo_description,
        stargazers_count,
        valid_from
    from changes
    where
        prev_repo_language is null
        or repo_language is distinct from prev_repo_language
        or repo_description is distinct from prev_repo_description
        or stargazers_count is distinct from prev_stargazers_count
),

versioned as (
    select
        to_hex(md5(concat(f.repo_name, cast(f.valid_from as string))))
            as repo_version_key,
        f.repo_name,
        f.repo_id,
        f.repo_language,
        f.repo_description,
        f.stargazers_count,
        f.valid_from,
        lead(f.valid_from)
            over (partition by f.repo_name order by f.valid_from)
            as valid_to
    from filtered as f
)

select
    repo_version_key,
    repo_name,
    repo_id,
    repo_language,
    repo_description,
    stargazers_count,
    valid_from,
    valid_to,
    valid_to is null as is_current
from versioned
