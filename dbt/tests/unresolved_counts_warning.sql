{{ config(severity='warn') }}
select count_status, count(*) as cells from {{ ref('int_vehicle_registrations__unpivoted') }} where count_status <> 'reported' group by count_status
