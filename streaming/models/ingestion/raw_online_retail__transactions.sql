{% set source_path = var("source_path") | replace("'", "''") %}
{% set limit_rows = var("limit_rows", 0) | int %}

with source_rows as (
    select *, row_number() over ()::bigint as source_row
    from read_csv(
        '{{ source_path }}',
        header = true,
        delim = ',',
        quote = '"',
        escape = '"',
        null_padding = true,
        all_varchar = true
    )
),
limited_rows as (
    select * from source_rows
    {% if limit_rows > 0 %}
    where source_row <= {{ limit_rows }}
    {% endif %}
)
select
    *,
    '{{ source_path }}' as source_file,
    current_timestamp as loaded_at
from limited_rows