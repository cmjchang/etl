select distinct vehicle_key, body_type, make, generic_model, model, fuel_type,
  is_unknown_make, is_unknown_generic_model, is_unknown_model
from {{ ref('vehicle_registrations') }}
