# Vehicle pipeline design

The dbt model graph uses ingestion/source -> staging -> intermediate -> core and
reporting marts -> export. See [dbt documentation](src/dbt/README.md) and
[DuckDB documentation](duckdb/README.md) for the existing transformation rules.

The separate local retail streaming exercise has its own dbt project under
`src/streaming/`, with raw, staging, and intermediate models in
`src/streaming/dbt_project.yml`. It uses `src/streaming/streaming.duckdb` and does not
participate in the vehicle pipeline.

`dim_vehicle` declares `unique_key='vehicle_key'` while retaining full-table
materialization. This configuration does not enable incremental loading or
enforce uniqueness; the dimension still uses `select distinct` and a `unique`
column test.


## Per-model schema tests and tags — 7 October 2026

Each SQL model has an adjacent YAML file containing its description, column
tests, and model configuration. Every model has the `dvla` tag plus its folder
layer: `ingestion`, `staging`, `intermediate`, `marts`, or `export`. Core and
reporting models both use `marts`. Existing export configuration is retained.
The former shared `models/schema.yml` has no model entries, avoiding duplicate
definitions.

Tests cover required metadata and cleaned keys, dimension uniqueness, fact
relationships, count statuses, quarter coverage, annual count completeness,
ranking eligibility, and export row equality. Existing singular tests retain
the source, unpivot, fact, and annual reconciliation checks. Source identity
nulls and suppressed counts remain permitted. Winner ties remain permitted;
ranked reports and their exports may legitimately be empty.

Shared generic tests are defined in `src/dbt/tests/generic/dvla_schema_tests.sql`.
From the dbt folder, use the project virtual environment to run
`python -m dbt.cli.main test --profiles-dir . --select tag:dvla`.
Select a layer with `--select tag:intermediate`, or intersect selections with
`--select tag:dvla,tag:marts`. Model tags also select attached tests through dbt's
indirect selection.

## Reproducible Builds and CI

From the root, `python src/dbt/run_pipeline.py` builds an isolated DuckDB database
from the checked-in synthetic CSV. No source download or existing database is
needed. The six categories across ten quarters produce 60 fact rows and exercise
ties, unknown identities, suppressed counts, and incomplete-year coverage.
Sample values are not official statistics.

Raw ingestion accepts `source_csv_path`; the runner passes an absolute local path
or an explicitly supplied URL. Direct dbt invocations without the variable retain
the public CSV URL. Staging, intermediate, and mart business rules are unchanged.
Use `--source`, `--database`, and `--export-root` for separate full-data runs.

The cross-platform runner uses its active Python environment and defaults to
`.artifacts/vehicle-demo.duckdb`. `VEHICLE_DB_PATH` supports direct dbt commands;
the runner's `--database` takes precedence. The streaming database is unaffected.

Non-export model tests gate all delivery work. Nine export models produce the
three reports in CSV, JSON, and Parquet. Export view equality tests and independent
file comparisons must pass before `_SUCCESS.json` and the atomic `latest.json`
publication. Failure preserves the previous pointer, not a database-wide snapshot.

GitHub Actions runs the temporary-database regression tests and the sample build
for pull requests and pushes to `main`. Both dbt stages retain distinct manifests,
run results, and logs. Available artifacts are uploaded even on failure. The
workflow requires no cloud secrets; branch protection must separately require
the **DuckDB Build and Test** check to prevent merging a failed PR.
