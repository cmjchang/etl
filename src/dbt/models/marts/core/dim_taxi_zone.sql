select
    location_id,
    borough,
    zone,
    service_zone
from {{ ref('int_nyctlc__taxi_zone_lookup') }}
