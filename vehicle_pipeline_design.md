# Vehicle pipeline design

The dbt model graph uses ingestion/source -> staging -> intermediate -> core and
reporting marts -> export. See [dbt documentation](dbt/README.md) and
[DuckDB documentation](duckdb/README.md) for the existing transformation rules.


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

Shared generic tests are defined in `dbt/tests/generic/dvla_schema_tests.sql`.
From the dbt folder, use the project virtual environment to run
`python -m dbt.cli.main test --profiles-dir . --select tag:dvla`.
Select a layer with `--select tag:intermediate`, or intersect selections with
`--select tag:dvla,tag:marts`. Model tags also select attached tests through dbt's
indirect selection.
