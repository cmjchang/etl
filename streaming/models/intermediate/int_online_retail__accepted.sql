with numbered as (
    select
        *,
        row_number() over (order by invoice_date, source_row) - 1 as accepted_row
    from {{ ref('stg_online_retail__transactions') }}
    where rejection_reasons = ''
)

select
    source_row,
    invoice_no,
    stock_code,
    description,
    quantity,
    invoice_date,
    unit_price,
    customer_id,
    country
from numbered