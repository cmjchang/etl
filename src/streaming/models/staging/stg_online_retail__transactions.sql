{% set date_format = var("date_format") | replace("'", "''") %}

with typed_values as (
    select
        source_row,
        source_file,
        loaded_at,
        InvoiceNo as invoice_no_raw,
        StockCode as stock_code_raw,
        Description as description_raw,
        Quantity as quantity_raw,
        InvoiceDate as invoice_date_raw,
        UnitPrice as unit_price_raw,
        CustomerID as customer_id_raw,
        Country as country_raw,
        nullif(trim(InvoiceNo), '') as invoice_no,
        nullif(trim(StockCode), '') as stock_code,
        nullif(trim(Description), '') as description,
        try_cast(nullif(trim(Quantity), '') as bigint) as quantity,
        try_strptime(nullif(trim(InvoiceDate), ''), '{{ date_format }}') as invoice_date,
        try_cast(nullif(trim(UnitPrice), '') as decimal(18, 4)) as unit_price,
        nullif(trim(CustomerID), '') as customer_id,
        nullif(trim(Country), '') as country
    from {{ ref('raw_online_retail__transactions') }}
),
classified as (
    select
        *,
        concat_ws('; ',
            case when invoice_no is null then 'missing InvoiceNo' end,
            case when stock_code is null then 'missing StockCode' end,
            case when country is null then 'missing Country' end,
            case
                when not regexp_matches(trim(quantity_raw), '^[+-]?[0-9]+$')
                    or quantity is null
                then 'invalid or overflowing Quantity'
            end,
            case
                when not regexp_matches(
                    trim(unit_price_raw),
                    '^[+-]?([0-9]+([.][0-9]{1,4})?|[.][0-9]{1,4})$'
                ) or unit_price is null
                then 'invalid, inexact, or overflowing UnitPrice'
            end,
            case when invoice_date is null then 'invalid or missing InvoiceDate' end
        ) as rejection_reasons
    from typed_values
)
select * from classified