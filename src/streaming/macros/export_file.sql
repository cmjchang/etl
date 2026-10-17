{% materialization export_file, adapter='duckdb' %}
  {% set relation = this.incorporate(type='view') %}
  {% set export_settings = config.get('meta', {}).get('export', {}) %}
  {% set file_format = export_settings.get('file_format') %}
  {% set output_name = export_settings.get('output_name') %}
  {% if not output_name %}
    {{ exceptions.raise_compiler_error('Missing meta.export.output_name') }}
  {% endif %}
  {% if file_format not in ['csv', 'json', 'parquet'] %}
    {{ exceptions.raise_compiler_error('Unsupported export format') }}
  {% endif %}
  {% set path = var('export_dir') ~ '/' ~ output_name ~ '.' ~ file_format %}
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
