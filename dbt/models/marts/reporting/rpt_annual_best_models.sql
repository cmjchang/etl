select * from {{ ref('rpt_annual_model_rankings') }} where registration_rank = 1
