{% materialization export_file_trunk, adapter='duckdb' %}
  {% set relation = this.incorporate(type='view') %}
  {% set export_settings = config.get('meta', {}).get('export', {}) %}
  {% set file_format = export_settings.get('file_format') %}
  {% set output_name = export_settings.get('output_name') %}
  {% set partition_column = export_settings.get('partition_column') %}
  
  {% if not output_name %}
    {{ exceptions.raise_compiler_error('Missing meta.export.output_name') }}
  {% endif %}
  {% if not partition_column %}
    {{ exceptions.raise_compiler_error('Missing meta.export.partition_column') }}
  {% endif %}
  {% if file_format not in ['csv', 'json', 'parquet'] %}
    {{ exceptions.raise_compiler_error('Unsupported export format') }}
  {% endif %}

  -- 1. Create or replace the view using the model's SQL body
  {% call statement('main') %}
    create or replace view {{ relation }} as {{ sql }}
  {% endcall %}

  -- 2. Query distinct partition/chunk IDs dynamically from the view
  {% set partition_query = "select distinct " ~ partition_column ~ " from " ~ relation ~ " order by 1" %}
  {% set results = run_query(partition_query) %}
  
  {% if execute %}
    {% set partition_values = results.columns[0].values() %}
  {% else %}
    {% set partition_values = [] %}
  {% endif %}

  {{ log("Exporting " ~ partition_values | length ~ " files partitioned by " ~ partition_column ~ "...", info=true) }}

  -- 3. Loop through each unique partition value and export its slice
  {% for val in partition_values %}
    {% call statement('write_file_' ~ val) %}
      {% set path = var('export_dir') ~ '/' ~ output_name ~ "_%04d" | format(val | int) ~ '.' ~ file_format %}  
      copy (
        select * from {{ relation }} where {{ partition_column }} = {{ val }}
      ) to '{{ path | replace("'", "''") }}'
        (format {{ file_format }}{% if file_format == 'csv' %}, header true{% endif %}{% if file_format == 'json' %}, array true{% endif %})
    {% endcall %}
  {% endfor %}

  {% do adapter.commit() %}
  {{ return({'relations': [relation]}) }}
{% endmaterialization %}