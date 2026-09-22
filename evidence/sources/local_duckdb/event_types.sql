select
    event_type,
    count(*) as events
from silver.stg_github_events
group by event_type
order by events desc
