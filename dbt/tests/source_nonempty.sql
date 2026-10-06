select 1 where not exists(select 1 from {{ ref('raw_dvla__vehicle_registrations') }})
