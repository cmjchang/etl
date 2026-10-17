select *
from {{ ref('stg_online_retail__transactions') }}
where rejection_reasons <> ''