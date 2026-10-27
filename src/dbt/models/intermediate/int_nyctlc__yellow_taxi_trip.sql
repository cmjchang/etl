{{ config(materialized='view') }}

select * rename (PULocationID as pickup_location_id, DOLocationID as dropoff_location_id)
from {{ ref('raw_nyctlc__yellow_taxi_trip') }}
