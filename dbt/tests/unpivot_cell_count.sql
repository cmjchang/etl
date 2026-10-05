select 1 where (select count(*) from {{ ref('vehicle_registrations') }}) <> (select count(*) from {{ ref('veh0160_raw') }}) * (select count(*) from {{ ref('dim_quarter') }})
