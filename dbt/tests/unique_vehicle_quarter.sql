select vehicle_key, quarter_key from {{ ref('vehicle_registrations') }} group by all having count(*) > 1
