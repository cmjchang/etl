{% set source_path = 'https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv' %}
select *, '{{ source_path }}' as source_file, current_timestamp as loaded_at
from read_csv('{{ source_path }}', header=true)
