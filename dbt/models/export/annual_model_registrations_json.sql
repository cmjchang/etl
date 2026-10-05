{{ config(file_format='json', output_name='annual_model_registrations') }}
select * from {{ ref('annual_model_registrations') }}
order by year, body_type, make, generic_model
