select
    vehicle_key,
    quarter_key,
    registration_count,
    count_status
from {{ ref('int_vehicle_registrations__unpivoted') }}
