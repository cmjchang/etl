{{ config(file_format='parquet', output_name='annual_best_models') }}
select * from {{ ref('annual_best_models') }}
order by year, body_type, registration_rank, make, generic_model
