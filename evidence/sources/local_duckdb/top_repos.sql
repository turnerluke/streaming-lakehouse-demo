select
    repo_name,
    count(*) as events,
    count(distinct actor_login) as unique_actors,
    count(distinct event_type) as event_types
from silver.stg_github_events
group by repo_name
order by events desc
