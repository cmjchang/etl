{{ 
config(materialized='export_file_trunk', 
meta={'export': {'file_format': 'parquet', 'output_name': 'batch', 'partition_column': 'batch_id'}}) 
}}

select *, cast(floor(source_row / {{ var('rows_per_chunk') }}) as bigint) as batch_id
from {{ ref('int_online_retail__accepted') }}