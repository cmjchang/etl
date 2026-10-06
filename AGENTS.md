# Documentation and layer conventions

Whenever general dbt or SQL logic changes, update these Markdown files in the same change:

- `vehicle_pipeline_design.md`
- `dbt/README.md`
- `duckdb/README.md`

Keep root README links and summary consistent with those documents.

Use conventional dbt layers: sources/raw -> staging -> intermediate -> marts.
Staging models use stg_<source>__<entity>; intermediate models use int_ prefixes.
Final facts and dimensions live in marts/core with fct_ and dim_ prefixes.
Reporting models live in marts/reporting with rpt_ prefixes. Export models use
export_<report>__<format>. Keep model references, schemas, export validators,
and documentation consistent when renaming.
