{{ config(meta={'export': {'file_format': 'csv', 'output_name': 'annual_model_registrations'}}) }}
select * from {{ ref('rpt_annual_model_registrations') }}
order by year, body_type, make, generic_model
