-- ISO day of week: 1 = Monday ... 7 = Sunday.
select
    dataset,
    isodow(pickup_date) as day_of_week,
    dayname(pickup_date) as day_name,
    pickup_hour,
    sum(trip_count) as trip_count,
    count(distinct pickup_date) as day_count,
    sum(trip_count) / count(distinct pickup_date) as avg_trips_per_day
from {{ ref('rpt_nyctlc_trip_hourly') }}
group by all
