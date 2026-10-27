{{ config(materialized='view') }}

select * exclude (source_file, loaded_at)
from {{ ref('int_nyctlc__green_taxi_trip') }}
