-- depends_on: {{ ref('raw_dvla__vehicle_registrations') }}
-- depends_on: {{ ref('int_vehicle_registrations__unpivoted') }}
{% if execute %}
{% set cols = adapter.get_columns_in_relation(ref('raw_dvla__vehicle_registrations')) %}
with source_counts as (
{% for col in cols if modules.re.fullmatch('[0-9]{4} Q[1-4]', col.name) %}
  select '{{ col.name }}' as period_label,
    sum(try_cast("{{ col.name }}" as bigint)) as total,
    count(*) filter(where "{{ col.name }}" is null or trim("{{ col.name }}") = '') as missing,
    count(*) filter(where trim("{{ col.name }}") = '[c]') as confidential,
    count(*) filter(where trim("{{ col.name }}") = '[x]') as unavailable,
    count(*) filter(where trim("{{ col.name }}") = '[z]') as not_applicable
  from {{ ref('raw_dvla__vehicle_registrations') }}
  {% if not loop.last %}union all{% endif %}
{% endfor %}
), cleaned as (
  select period_label, sum(registration_count) as total,
    count(*) filter(where count_status='missing') as missing,
    count(*) filter(where count_status='confidential') as confidential,
    count(*) filter(where count_status='unavailable') as unavailable,
    count(*) filter(where count_status='not_applicable') as not_applicable
  from {{ ref('int_vehicle_registrations__unpivoted') }} group by period_label
)
select s.period_label from source_counts s full join cleaned c using(period_label)
where s.total is distinct from c.total or s.missing is distinct from c.missing
or s.confidential is distinct from c.confidential or s.unavailable is distinct from c.unavailable
or s.not_applicable is distinct from c.not_applicable
{% else %}select 1 where false{% endif %}
