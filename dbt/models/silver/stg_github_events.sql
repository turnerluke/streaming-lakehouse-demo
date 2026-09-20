with source as (
    select * from {{ source('bronze', 'raw_events') }}
),

typed as (
    select
        event_id,
        event_type,
        actor_login,
        repo_name,
        cast(event_created_at as timestamp) as event_created_at,
        ingested_at,
        json_value(payload, '$.payload.action') as action,
        json_value(payload, '$.payload.ref') as ref,
        json_value(payload, '$.payload.ref_type') as ref_type,
        json_value(payload, '$.public') as is_public,
        payload
    from source
),

deduped as (
    select *
    from typed
    qualify
        row_number() over (partition by event_id order by ingested_at desc) = 1
)

select * from deduped
