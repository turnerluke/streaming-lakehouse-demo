select
    valid_from,
    repo_language as language,
    repo_description as description,
    stargazers_count as stars,
    case when is_current then 'current' else '' end as flag
from gold.dim_repo_scd2
where repo_name = 'octocat/hello-world'
order by valid_from
