select
    repo_name,
    count(*) as version_count
from gold.dim_repo_scd2
group by repo_name
order by version_count desc
