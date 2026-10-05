{{ config(severity='warn') }}
select count_status, count(*) as cells from {{ ref('vehicle_registrations') }} where count_status <> 'reported' group by count_status
