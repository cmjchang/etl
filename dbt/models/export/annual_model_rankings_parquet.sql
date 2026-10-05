{{ config(file_format='parquet', output_name='annual_model_rankings') }}
select * from {{ ref('annual_model_rankings') }}
order by year, body_type, registration_rank, make, generic_model
