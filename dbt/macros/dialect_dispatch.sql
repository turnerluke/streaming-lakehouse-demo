{#
    Adapter-dispatched helpers so the same model SQL runs on both
    BigQuery (cloud target) and DuckDB (local target). Add a new
    `<adapter>__<name>` implementation when a third target lands.
#}

{% macro json_get(column, path) %}
    {{ return(adapter.dispatch('json_get')(column, path)) }}
{% endmacro %}

{% macro default__json_get(column, path) %}
    json_value({{ column }}, '{{ path }}')
{% endmacro %}

{% macro duckdb__json_get(column, path) %}
    json_extract_string({{ column }}, '{{ path }}')
{% endmacro %}


{% macro trunc_hour(ts) %}
    {{ return(adapter.dispatch('trunc_hour')(ts)) }}
{% endmacro %}

{% macro default__trunc_hour(ts) %}
    timestamp_trunc({{ ts }}, hour)
{% endmacro %}

{% macro duckdb__trunc_hour(ts) %}
    date_trunc('hour', {{ ts }})
{% endmacro %}


{% macro hours_ago(n) %}
    {{ return(adapter.dispatch('hours_ago')(n)) }}
{% endmacro %}

{% macro default__hours_ago(n) %}
    timestamp_sub(current_timestamp(), interval {{ n }} hour)
{% endmacro %}

{% macro duckdb__hours_ago(n) %}
    current_timestamp - interval ({{ n }}) hour
{% endmacro %}


{#
    BigQuery's `to_hex(md5(x))` returns hex-encoded BYTES; DuckDB's
    `md5(x)` already returns a hex VARCHAR, so wrapping with `to_hex`
    would double-encode. Dispatch keeps the fingerprint string
    identical across dialects.
#}
{% macro hex_md5(x) %}
    {{ return(adapter.dispatch('hex_md5')(x)) }}
{% endmacro %}

{% macro default__hex_md5(x) %}
    to_hex(md5({{ x }}))
{% endmacro %}

{% macro duckdb__hex_md5(x) %}
    md5({{ x }})
{% endmacro %}
