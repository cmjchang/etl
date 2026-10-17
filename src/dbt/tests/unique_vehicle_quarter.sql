select vehicle_key, quarter_key from {{ ref('int_vehicle_registrations__unpivoted') }} group by all having count(*) > 1
