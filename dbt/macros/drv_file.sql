{% materialization drv_file, adapter='duckdb' %}
  {% set relation = this.incorporate(type='view') %}
  {% set file_format = config.get('file_format') %}
  {% if file_format not in ['csv', 'json', 'parquet'] %}
    {{ exceptions.raise_compiler_error('Unsupported export format') }}
  {% endif %}
  {% set path = var('export_dir') ~ '/' ~ config.get('output_name') ~ '.' ~ file_format %}
  {% call statement('main') %}
    create or replace view {{ relation }} as {{ sql }}
  {% endcall %}
  {% call statement('write_file') %}
    copy (select * from {{ relation }}) to '{{ path | replace("'", "''") }}'
      (format {{ file_format }}{% if file_format == 'csv' %}, header true{% endif %}{% if file_format == 'json' %}, array true{% endif %})
  {% endcall %}
  {% do adapter.commit() %}
  {{ return({'relations': [relation]}) }}
{% endmaterialization %}
