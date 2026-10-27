{% macro nyctlc_trip_ingestion(dataset) %}
{% set source_path = var('source_csv_path', none) %}
{% set paths = [] %}
{% if source_path is not none %}
  {% do paths.append(source_path) %}
{% else %}
  {% set end_month = var('nyctlc_end_month', 7) %}
  {% if end_month is not integer or end_month < 1 or end_month > 12 %}
    {{ exceptions.raise_compiler_error('nyctlc_end_month must be an integer from 1 to 12 (inclusive), for 2026.') }}
  {% endif %}
  {% for year in [2025, 2026] %}
    {% for month in range(1, (12 if year == 2025 else end_month) + 1) %}
      {% do paths.append('https://d37ci6vzurychx.cloudfront.net/trip-data/' ~ dataset ~ '_tripdata_' ~ year ~ '-' ~ '%02d' | format(month) ~ '.parquet') %}
    {% endfor %}
  {% endfor %}
{% endif %}
{# Incremental runs skip files already recorded in source_file; --full-refresh reloads everything. #}
{% set loaded = [] %}
{% if execute and is_incremental() %}
  {% for row in run_query('select distinct source_file from ' ~ this).rows %}
    {% do loaded.append(row[0]) %}
  {% endfor %}
{% endif %}
{% set pending = paths | reject('in', loaded) | list %}
{% if pending | length == 0 %}
select * from {{ this }} where false
{% else %}
select * exclude (filename), filename as source_file, current_timestamp as loaded_at
from read_parquet(
  [
    {% for path in pending %}
    '{{ path | replace("'", "''") }}'{% if not loop.last %},{% endif %}
    {% endfor %}
  ],
  union_by_name=true,
  filename=true
)
{% endif %}
{% endmacro %}
