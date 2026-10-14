{{ config(materialized='export_file_trunk', meta={'export': {'file_format': 'csv', 'output_name': 'export_online_retail__accepted', 'partition_column': 'batch_id'}}) }}

select *, (ROW_NUMBER() OVER () - 1) // 10000 AS batch_id
from {{ ref('int_online_retail__accepted') }}