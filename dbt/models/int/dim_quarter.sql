with quarters as (
  select distinct quarter_key, period_label, year, quarter_number, quarter_start_date
  from {{ ref('vehicle_registrations') }}
)
select *, cast(quarter_start_date + interval '3 months' - interval '1 day' as date) as quarter_end_date,
  count(*) over (partition by year) as quarters_available,
  min(quarter_number) over (partition by year) as first_available_quarter,
  max(quarter_number) over (partition by year) as last_available_quarter
from quarters
