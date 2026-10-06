{{ config(meta={'export': {'file_format': 'csv', 'output_name': 'annual_best_models'}}) }}

select * 
from {{ ref('rpt_annual_best_models') }}
order by year desc, body_type, registration_rank, make, generic_model
