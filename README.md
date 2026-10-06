
## Vehicle analytics dbt pipeline

Conventional layers: raw sources -> staging -> intermediate -> marts/core and
marts/reporting -> exports. The database is my_database.duckdb. Models use stg_,
int_, dim_, fct_, and rpt_ prefixes. From dbt/, run
`.\.venv\Scripts\python.exe .\run_pipeline.py`.

Documentation: dbt/README.md, vehicle_pipeline_design.md, duckdb/README.md.
Keep these files updated whenever dbt/SQL logic changes. For one-time verified
old-name retirement, use dbt/migrate_model_names.py.
