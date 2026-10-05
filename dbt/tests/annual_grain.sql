select year, body_type, make, generic_model from {{ ref('annual_model_registrations') }} group by all having count(*) > 1
