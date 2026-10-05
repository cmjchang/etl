select BodyType, Make, GenModel, Model, Fuel from {{ ref('veh0160_raw') }} group by all having count(*) > 1
