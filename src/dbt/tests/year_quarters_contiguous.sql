select year from {{ ref('dim_quarter') }} group by year having count(*) <> max(quarter_number) - min(quarter_number) + 1
