with unpivoted as (
  select * from {{ ref('stg_dvla__vehicle_registrations') }}
  unpivot include nulls (raw_count for quarter_column in (columns('^registrations_[0-9]{4}_q[1-4]$')))
) , long as (
  select * exclude (quarter_column),
    regexp_extract(quarter_column, '([0-9]{4})_q([1-4])', 1)
      || ' Q' || regexp_extract(quarter_column, '([0-9]{4})_q([1-4])', 2) as period_label
  from unpivoted
), cleaned as (
  select
    coalesce(nullif(trim(body_type), ''), 'UNKNOWN') as body_type,
    coalesce(nullif(trim(make), ''), 'UNKNOWN') as make,
    coalesce(nullif(trim(generic_model), ''), 'UNKNOWN') as generic_model,
    coalesce(nullif(trim(model), ''), 'UNKNOWN') as model,
    coalesce(nullif(trim(fuel_type), ''), 'UNKNOWN') as fuel_type,
    period_label, raw_count, source_file, loaded_at,
    cast(left(period_label, 4) as integer) as year,
    cast(right(period_label, 1) as integer) as quarter_number,
    case
      when raw_count is null or trim(raw_count) = '' then 'missing'
      when trim(raw_count) = '[c]' then 'confidential'
      when trim(raw_count) = '[x]' then 'unavailable'
      when trim(raw_count) = '[z]' then 'not_applicable'
      when regexp_full_match(trim(raw_count), '[0-9]+')
           and try_cast(trim(raw_count) as bigint) is not null then 'reported'
      else 'invalid'
    end as count_status
  from long
), typed as (
  select *,
    make_date(year, (quarter_number - 1) * 3 + 1, 1) as quarter_start_date,
    case when count_status = 'reported' then cast(trim(raw_count) as bigint) end as registration_count,
    upper(make) in ('UNKNOWN', 'MAKE MISSING', 'MODEL MISSING') as is_unknown_make,
    upper(generic_model) = 'UNKNOWN' or upper(generic_model) like '%MODEL MISSING' as is_unknown_generic_model,
    upper(model) in ('UNKNOWN', 'MODEL MISSING') as is_unknown_model
  from cleaned
)
select *,
  md5(to_json(list_value(body_type, make, generic_model, model, fuel_type))) as vehicle_key,
  year * 10 + quarter_number as quarter_key
from typed
