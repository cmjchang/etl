-- depends_on: {{ ref('raw_dvla__vehicle_registrations') }}
{{ validate_source() }}
{% set ns = namespace(quarters=[]) %}
{% if execute %}
  {% for col in adapter.get_columns_in_relation(source('dvla', 'vehicle_registrations')) %}
    {% if modules.re.fullmatch('[0-9]{4} Q[1-4]', col.name) %}
      {% do ns.quarters.append(col.name) %}
    {% endif %}
  {% endfor %}
{% endif %}
select
  BodyType as body_type,
  Make as make,
  GenModel as generic_model,
  Model as model,
  Fuel as fuel_type,
  {% for quarter in ns.quarters %}
  "{{ quarter }}" as registrations_{{ quarter[:4] }}_q{{ quarter[-1] }},
  {% endfor %}
  source_file,
  loaded_at
from {{ source('dvla', 'vehicle_registrations') }}
