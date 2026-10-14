
## Vehicle analytics dbt pipeline

Conventional layers: raw sources -> staging -> intermediate -> marts/core and
marts/reporting -> exports. The database is my_database.duckdb. Models use stg_,
int_, dim_, fct_, and rpt_ prefixes.

## Setup and run

From the repository root, sync dependencies, then run dbt:

```sh
uv sync
cd dbt
dbt run
```

Documentation: [dbt/README.md](dbt/README.md),
[vehicle_pipeline_design.md](vehicle_pipeline_design.md),
[duckdb/README.md](duckdb/README.md).
Keep these files updated whenever dbt/SQL logic changes. For one-time verified
old-name retirement, use dbt/migrate_model_names.py.

The separate local PySpark Structured Streaming exercise is documented in
[streaming/README.md](streaming/README.md). Its own dbt project prepares the raw
retail CSV in DuckDB before Python publishes Parquet chunks; it does not change
the vehicle dbt pipeline or `my_database.duckdb`.
