select
    count(*) as total_events,
    count(distinct actor_login) as unique_actors,
    count(distinct repo_name) as unique_repos,
    count(distinct event_type) as event_types
from silver.stg_github_events
