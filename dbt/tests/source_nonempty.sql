select 1 where not exists(select 1 from {{ ref('veh0160_raw') }})
