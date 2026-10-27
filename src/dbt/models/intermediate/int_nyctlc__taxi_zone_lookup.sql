{{ config(materialized='view') }}

select * rename (LocationID as location_id)
from {{ ref('raw_nyctlc__taxi_zone_lookup') }}
