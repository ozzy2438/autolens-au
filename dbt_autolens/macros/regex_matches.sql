{% macro regex_matches(column_expression, pattern) -%}
    {{ return(adapter.dispatch('regex_matches', 'autolens_au')(column_expression, pattern)) }}
{%- endmacro %}

{% macro default__regex_matches(column_expression, pattern) -%}
    ({{ column_expression }} ~* '{{ pattern }}')
{%- endmacro %}

{% macro snowflake__regex_matches(column_expression, pattern) -%}
    regexp_like({{ column_expression }}, '{{ pattern }}', 'i')
{%- endmacro %}
