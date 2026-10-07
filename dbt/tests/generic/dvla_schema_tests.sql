{% test dvla_nonempty(model) %}
select 1 as empty_model where not exists (select 1 from {{ model }})
{% endtest %}

{% test dvla_unique_columns(model, column_names) %}
select {% for column in column_names %}{{ adapter.quote(column) }}{% if not loop.last %}, {% endif %}{% endfor %}, count(*) as row_count
from {{ model }}
group by {% for column in column_names %}{{ adapter.quote(column) }}{% if not loop.last %}, {% endif %}{% endfor %}
having count(*) > 1
{% endtest %}

{% test dvla_expression_is_true(model, expression) %}
select * from {{ model }} where ({{ expression }}) is distinct from true
{% endtest %}

{% test dvla_same_rows(model, compare_model) %}
(select * from {{ model }} except all select * from {{ compare_model }})
union all
(select * from {{ compare_model }} except all select * from {{ model }})
{% endtest %}
