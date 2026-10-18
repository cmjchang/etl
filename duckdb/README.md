# DuckDB Storage and Validation

The vehicle dbt project lives in [src/dbt](../src/dbt/README.md).
This directory contains documentation, not a second dbt project.

## Reproducible Sample

After following the [root setup](../README.md), run from the repository root:

```sh
python src/dbt/run_pipeline.py
```

The runner creates `.artifacts/vehicle-demo.duckdb` from the checked-in synthetic
CSV. No existing DuckDB file, source download, or credentials are required.
It uses dbt Core 1.12.5, dbt-duckdb 1.11.0, and DuckDB 1.5.5 on Python 3.12.
Sample data are original demonstration values, not official DVLA statistics.

## Schemas and Grain

- `raw`: source strings plus source path and load timestamp.
- `staging`: value-preserving identity/quarter aliases.
- `intermediate`: null-preserving unpivot and typed/status-bearing counts.
- `core`: vehicle and quarter dimensions, plus the vehicle-quarter fact table.
- `reporting`: annual totals, eligible rankings, and best-model reports.
- `vehicle_export`: nine lightweight views backing file deliveries.

The sample has six categories and ten quarters, producing 60 fact rows.
Suppressed, unavailable, not-applicable, and missing counts remain distinguishable.
See [business rules](../vehicle_pipeline_design.md) for ranking eligibility.

## Paths and Operations

`--database` sets the runner's database path and overrides `VEHICLE_DB_PATH`.
Without either, the runner uses the isolated sample database. Direct dbt commands
read `VEHICLE_DB_PATH`, defaulting to `my_database.duckdb` in their working
directory. Set the override explicitly when inspecting or testing demo models.

```sh
python src/dbt/run_pipeline.py --source /absolute/path/to/input.csv --database .artifacts/vehicle-full.duckdb --export-root .artifacts/full-exports
```

Keep sample and full-data outputs separate, and run one writer at a time.
The runner does not modify the independent streaming project's database.
Generated databases and demo outputs are ignored by Git.

## Delivery and Quality Gates

The runner tests non-export models, builds and tests nine export views, then reads
every generated CSV, JSON, and Parquet file back through DuckDB. Comparisons use
the reporting column types and bidirectional `EXCEPT ALL`, preserving duplicate
multiplicity. Empty reports are valid; mismatched files prevent publication.

Validated batches receive `_SUCCESS.json`; `.artifacts/exports/latest.json` is
replaced atomically only on success. A failed run leaves that pointer unchanged,
but model updates are not rolled back as one project-wide transaction.

GitHub CI runs this same sample pipeline and regression tests without committing
database binaries. It retains manifests and run results for both dbt stages,
logs, and export batches for 14 days. See the
[workflow](../.github/workflows/dbt-ci.yml) and
[regression tests](../src/dbt/tests/test_run_pipeline.py).