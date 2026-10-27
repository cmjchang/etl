-- Single scan of fct_trip; all other NYC TLC reports roll up from this grain.
select
    dataset,
    date_trunc('day', pickup_at)::date as pickup_date,
    hour(pickup_at) as pickup_hour,
    payment_type_id,
    count(*) as trip_count,
    sum(trip_miles) as trip_miles,
    sum(fare_amount) as fare_amount,
    sum(tip_amount) as tip_amount,
    sum(tolls_amount) as tolls_amount,
    sum(surcharge_amount) as surcharge_amount,
    sum(total_amount) as total_amount
from {{ ref('fct_trip') }}
where pickup_at is not null
group by all
