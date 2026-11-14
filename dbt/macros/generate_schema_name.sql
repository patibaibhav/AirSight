{% macro generate_schema_name(custom_schema_name, node) -%}
    {% set schema_name = custom_schema_name | trim if custom_schema_name else 'STAGING' %}
    {% if target.name == 'prod' %}
        {{ schema_name }}
    {% else %}
        DEV_{{ schema_name }}
    {% endif %}
{%- endmacro %}
