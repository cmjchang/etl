-- depends_on: {{ ref('veh0160_raw') }}
-- depends_on: {{ ref('veh0160_columns') }}
{% if execute %}
{% set cols = adapter.get_columns_in_relation(ref('veh0160_raw')) %}
with renamed_source as (
  select BodyType as body_type, Make as make, GenModel as generic_model,
    Model as model, Fuel as fuel_type,
    {% for col in cols if modules.re.fullmatch('[0-9]{4} Q[1-4]', col.name) %}
    "{{ col.name }}" as registrations_{{ col.name[:4] }}_q{{ col.name[-1] }},
    {% endfor %}
    source_file, loaded_at from {{ ref('veh0160_raw') }}
)
(select * from renamed_source except all select * from {{ ref('veh0160_columns') }})
union all
(select * from {{ ref('veh0160_columns') }} except all select * from renamed_source)
{% else %}select 1 where false{% endif %}
