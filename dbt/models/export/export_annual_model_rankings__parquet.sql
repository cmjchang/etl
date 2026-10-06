{{ config(meta={'export': {'file_format': 'parquet', 'output_name': 'annual_model_rankings'}}) }}
select * from {{ ref('rpt_annual_model_rankings') }}
order by year, body_type, registration_rank, make, generic_model
