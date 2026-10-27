{{ config(materialized='view') }}

select * exclude (source_file, loaded_at)
from {{ ref('int_nyctlc__yellow_taxi_trip') }}
