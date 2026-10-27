{{ config(materialized='view') }}

select * exclude (source_file, loaded_at)
from {{ ref('int_nyctlc__high_volume_for_hire_vehicle_trip') }}
