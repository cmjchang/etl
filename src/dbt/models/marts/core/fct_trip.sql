{{ config(materialized='view') }}

-- surcharge_amount = every fee beyond fare, tip and tolls; total_amount is rebuilt for HVFHV.
select
    'yellow' as dataset,
    tpep_pickup_datetime as pickup_at,
    pickup_location_id,
    dropoff_location_id,
    payment_type::integer as payment_type_id,
    trip_distance as trip_miles,
    fare_amount,
    tip_amount,
    tolls_amount,
    coalesce(extra, 0) + coalesce(mta_tax, 0) + coalesce(improvement_surcharge, 0)
        + coalesce(congestion_surcharge, 0) + coalesce(airport_fee, 0)
        + coalesce(cbd_congestion_fee, 0) as surcharge_amount,
    total_amount
from {{ ref('int_nyctlc__yellow_taxi_trip') }}

union all by name

select
    'green' as dataset,
    lpep_pickup_datetime as pickup_at,
    pickup_location_id,
    dropoff_location_id,
    payment_type::integer as payment_type_id,
    trip_distance as trip_miles,
    fare_amount,
    tip_amount,
    tolls_amount,
    coalesce(extra, 0) + coalesce(mta_tax, 0) + coalesce(improvement_surcharge, 0)
        + coalesce(congestion_surcharge, 0) + coalesce(ehail_fee, 0)
        + coalesce(cbd_congestion_fee, 0) as surcharge_amount,
    total_amount
from {{ ref('int_nyctlc__green_taxi_trip') }}

union all by name

select
    'hvfhv' as dataset,
    pickup_datetime as pickup_at,
    pickup_location_id,
    dropoff_location_id,
    null::integer as payment_type_id,
    trip_miles,
    base_passenger_fare as fare_amount,
    tips as tip_amount,
    tolls as tolls_amount,
    coalesce(bcf, 0) + coalesce(sales_tax, 0) + coalesce(congestion_surcharge, 0)
        + coalesce(airport_fee, 0) + coalesce(cbd_congestion_fee, 0) as surcharge_amount,
    coalesce(base_passenger_fare, 0) + coalesce(tolls, 0) + coalesce(tips, 0)
        + coalesce(bcf, 0) + coalesce(sales_tax, 0) + coalesce(congestion_surcharge, 0)
        + coalesce(airport_fee, 0) + coalesce(cbd_congestion_fee, 0) as total_amount
from {{ ref('int_nyctlc__high_volume_for_hire_vehicle_trip') }}
