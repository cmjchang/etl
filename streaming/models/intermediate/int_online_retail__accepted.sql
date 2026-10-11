{% set rows_per_chunk = var('rows_per_chunk', 50) | int %}

with numbered as (
    select
        *,
        row_number() over (order by invoice_date, source_row) - 1 as accepted_row
    from {{ ref('stg_online_retail__transactions') }}
    where rejection_reasons = ''
)
select
    source_row,
    cast(floor(accepted_row / {{ rows_per_chunk }}) as bigint) as batch_id,
    invoice_no,
    stock_code,
    description,
    quantity,
    invoice_date,
    unit_price,
    customer_id,
    country
from numbered