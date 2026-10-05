# Documentation and layer conventions

Whenever general dbt or SQL logic changes, update these Markdown files in the same change:

- `vehicle_pipeline_design.md`
- `dbt/README.md`
- `duckdb/README.md`

Keep root README links and summary consistent with those documents.

Use the layer convention `src -> cln -> int -> drv`: source ingestion;
snake_case aliases and cleaned records; canonical facts/dimensions;
derived analytics from those facts/dimensions. Keep export dependencies and
validators aligned with the current layer names.
