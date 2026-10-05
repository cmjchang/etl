with requested as (select unnest([{{ var('ranking_years') | join(', ') }}]) as year) select r.year from requested r left join {{ ref('dim_quarter') }} q using(year) where q.year is null
