select
    *,
    dense_rank() over (
        partition by year, body_type order by annual_registration_count desc
    ) as registration_rank
from {{ ref('rpt_annual_model_registrations') }}
where is_rank_eligible 
and year > extract(year from current_date) - 3