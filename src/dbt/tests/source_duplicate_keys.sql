select BodyType, Make, GenModel, Model, Fuel from {{ ref('raw_dvla__vehicle_registrations') }} group by all having count(*) > 1
