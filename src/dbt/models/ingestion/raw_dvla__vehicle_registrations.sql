{% set source_path = var('source_csv_path', 'https://assets.publishing.service.gov.uk/media/6aad4b1ef1f8d2a39605fa1b/df_VEH0160_UK.csv') %}
select *, '{{ source_path | replace("'", "''") }}' as source_file, current_timestamp as loaded_at
from read_csv('{{ source_path | replace("'", "''") }}', header=true, all_varchar=true)
