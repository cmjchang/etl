with annual as (
  select q.year, v.body_type, v.make, v.generic_model,
    coalesce(sum(f.registration_count), 0)::bigint as known_registration_count,
    count(*) filter (where f.count_status <> 'reported') as unresolved_cell_count,
    max(q.quarters_available) as quarters_available,
    min(q.first_available_quarter) as first_available_quarter,
    max(q.last_available_quarter) as last_available_quarter,
    bool_or(v.is_unknown_make or v.is_unknown_generic_model) as is_unknown_identity
  from {{ ref('fct_vehicle_registrations') }} f
  join {{ ref('dim_vehicle') }} v using (vehicle_key)
  join {{ ref('dim_quarter') }} q using (quarter_key)
  group by q.year, v.body_type, v.make, v.generic_model
), labeled as (
  select *,
    case when unresolved_cell_count = 0 then known_registration_count end as annual_registration_count,
    quarters_available = 4 as is_full_year,
    unresolved_cell_count = 0 as has_complete_counts,
    case when quarters_available = 4 then 'full_year'
         when first_available_quarter = 1 then 'year_to_date' else 'partial_year' end as coverage_label,
    sum(case when not is_unknown_identity then unresolved_cell_count else 0 end)
      over (partition by year, body_type) as comparison_unresolved_cells
  from annual
)
select *,
  not is_unknown_identity and comparison_unresolved_cells = 0 as is_rank_eligible,
  case when is_unknown_identity then 'unknown_identity'
       when comparison_unresolved_cells > 0 then 'incomplete_counts'
       else 'eligible' end as ranking_status
from labeled
