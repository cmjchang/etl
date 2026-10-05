select * from {{ ref('annual_model_rankings') }} where registration_rank = 1
