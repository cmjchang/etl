{% macro validate_source() %}
{% if execute %}
  {% set columns = adapter.get_columns_in_relation(ref('veh0160_raw')) %}
  {% set required = ['BodyType', 'Make', 'GenModel', 'Model', 'Fuel', 'source_file', 'loaded_at'] %}
  {% set names = columns | map(attribute='name') | list %}
  {% for name in required %}
    {% if name not in names %}{{ exceptions.raise_compiler_error('Missing source column: ' ~ name) }}{% endif %}
  {% endfor %}
  {% set ns = namespace(quarters=0) %}
  {% for name in names if name not in required %}
    {% if not modules.re.fullmatch('[0-9]{4} Q[1-4]', name) %}
      {{ exceptions.raise_compiler_error('Unexpected source header: ' ~ name) }}
    {% endif %}
    {% set ns.quarters = ns.quarters + 1 %}
  {% endfor %}
  {% if ns.quarters == 0 %}{{ exceptions.raise_compiler_error('No quarter columns') }}{% endif %}
{% endif %}
{% endmacro %}
