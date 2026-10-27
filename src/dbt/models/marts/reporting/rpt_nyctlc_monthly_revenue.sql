with monthly as (
    select
        dataset,
        date_trunc('month', pickup_date)::date as month_start,
        sum(trip_count) as trip_count,
        sum(trip_miles) as trip_miles,
        sum(fare_amount) as fare_amount,
        sum(tip_amount) as tip_amount,
        sum(tolls_amount) as tolls_amount,
        sum(surcharge_amount) as surcharge_amount,
        sum(total_amount) as total_amount
    from {{ ref('rpt_nyctlc_trip_hourly') }}
    group by all
)

select
    *,
    fare_amount / nullif(trip_count, 0) as avg_fare_per_trip,
    fare_amount / nullif(trip_miles, 0) as avg_fare_per_mile,
    total_amount / sum(total_amount) over (partition by month_start) as revenue_share
from monthly
