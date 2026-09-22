select
    event_hour,
    event_type,
    event_count
from gold.fct_events_hourly
order by event_hour, event_type
