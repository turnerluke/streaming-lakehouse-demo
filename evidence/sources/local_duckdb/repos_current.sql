select
    repo_name,
    repo_language,
    repo_description,
    stargazers_count,
    valid_from as first_seen
from gold.dim_repo_scd2
where is_current = true
order by stargazers_count desc
