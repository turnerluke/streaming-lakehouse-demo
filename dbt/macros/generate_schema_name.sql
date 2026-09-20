{#
    Custom `generate_schema_name` that adapts by target.

    - **DuckDB**: use the model's `+schema:` verbatim (`bronze`,
      `silver`, `gold`). dbt-duckdb's default would produce
      `main_bronze`/`main_silver`/`main_gold`, which fights our
      sources.yml and doesn't match the BQ dataset convention.

    - **BigQuery (and anything else)**: keep dbt's default behavior
      (`<target.schema>_<custom>`). That default is deliberate on
      cloud warehouses — it gives each developer an isolated set of
      datasets in a shared dev project. Overriding it globally would
      cause every dev to write to the same `bronze`/`silver`/`gold`
      datasets in a shared BQ project.
#}

{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- elif target.type == 'duckdb' -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
