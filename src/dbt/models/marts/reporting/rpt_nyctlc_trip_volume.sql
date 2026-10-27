with base as (
    select dataset, pickup_date, sum(trip_count) as trip_count
    from {{ ref('rpt_nyctlc_trip_hourly') }}
    group by all
)

select 'day' as period_type, pickup_date as period_start, dataset, sum(trip_count) as trip_count
from base group by all
union all
select 'week', date_trunc('week', pickup_date)::date, dataset, sum(trip_count)
from base group by all
union all
select 'month', date_trunc('month', pickup_date)::date, dataset, sum(trip_count)
from base group by all
union all
select 'year', date_trunc('year', pickup_date)::date, dataset, sum(trip_count)
from base group by all
