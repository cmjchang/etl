-- tip_pct is tip / fare; cash rows are flagged because cash tips are not recorded.
select
    h.dataset,
    coalesce(p.payment_type, 'Not applicable') as payment_type,
    coalesce(p.tips_recorded, true) as tips_recorded,
    sum(h.trip_count) as trip_count,
    sum(h.fare_amount) as fare_amount,
    sum(h.tip_amount) as tip_amount,
    sum(h.tip_amount) / nullif(sum(h.fare_amount), 0) as tip_pct
from {{ ref('rpt_nyctlc_trip_hourly') }} as h
left join {{ ref('dim_payment_type') }} as p using (payment_type_id)
group by all
