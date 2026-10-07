# Vehicle registration analytics: conventional dbt naming

Updated: 6 October 2026.

## Layers, folders, and physical schemas

| Folder | Schema | Models / responsibility |
|---|---|---|
| models/ingestion | raw | raw_dvla__vehicle_registrations: fixed CSV ingestion |
| models/staging/dvla | staging | stg_dvla__vehicle_registrations: snake_case aliases, value preserving |
| models/intermediate | intermediate | int_vehicle_registrations__unpivoted: null-preserving unpivot, cleaning and typing |
| models/marts/core | core | dim_vehicle, dim_quarter, fct_vehicle_registrations |
| models/marts/reporting | reporting | rpt_annual_model_registrations, rpt_annual_model_rankings, rpt_annual_best_models |
| models/export | vehicle_export | export_<report>__<format>: nine file exports |

Standard dbt model prefixes are stg_, int_, dim_, and fct_. This project also uses
rpt_ for reports and export_ for delivery models as explicit team conventions.
Folders and schemas are separate settings; schemas are configured in dbt_project.yml.

Raw ingestion is a small project-specific extension so one manual pipeline loads
the local CSV. The raw relation is declared as source('dvla', 'vehicle_registrations').
Staging selects through source(), with an explicit ref() dependency on ingestion
so a fresh database builds in order. Downstream models use ref().

## Paths and environment

Database: ../my_database.duckdb. Input: data/df_VEH0160_UK.csv.
The previous external duckdb folder was absent when renaming began. The CSV was
recovered from the former src.veh0160_raw database snapshot before retirement; it cannot recover
source text/symbols already lost before that snapshot. Runs do not download
the source again. Source columns are read as strings before transformation.

Use the project's isolated .venv, not the global dbt executable. Dependencies are
pinned in requirements.txt: dbt Core 1.12.5, dbt-duckdb 1.11.0, DuckDB 1.5.5.

```powershell
uv venv .venv --python 3.12
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
# Only when the fixed input CSV has not been prepared:
.\.venv\Scripts\python.exe .\prepare_source.py
```

## Run and migrate

Run from this dbt folder:

```powershell
.\.venv\Scripts\python.exe .\run_pipeline.py
```

For the one-time old-name retirement, use:

```powershell
.\.venv\Scripts\python.exe .\migrate_model_names.py
```

The migration builds and validates first, compares every old/new project table
(excluding source_file/loaded_at run metadata), and compares old/new export views. It retires matching
old objects transactionally, without CASCADE. It does not modify unrelated tables.
Normal builds do not perform retirement. Close other writers holding the database.

Individual commands:

```powershell
.\.venv\Scripts\dbt.exe debug --profiles-dir .
.\.venv\Scripts\dbt.exe build --profiles-dir . --exclude tag:export
.\.venv\Scripts\dbt.exe docs generate --profiles-dir .
```

## General SQL logic and business rules

Staging aliases BodyType -> body_type, Make -> make, GenModel -> generic_model,
Model -> model, Fuel -> fuel_type. Wide quarter columns become
registrations_YYYY_qN, without changing cell values. Intermediate unpivots only
those columns with INCLUDE NULLS and recovers period_label/year/quarter fields.
It trims labels, flags unknown identities, parses nonnegative BIGINT counts, and
preserves reported/confidential/unavailable/not_applicable/missing statuses.
Unexpected counts fail validation; unknown values never silently become zero.

Core dimensions define vehicle categories and source quarters. The fact grain is
vehicle_key + quarter_key. Deterministic vehicle keys use JSON-encoded attribute
tuples. Relationship/uniqueness tests protect joins and totals.

Reports rank generic models within body type for 2024, 2025, and 2026, combining
specific variants and fuels. 2026 Q1–Q2 participates as YTD. Full-year coverage is
metadata, not an eligibility filter. Annual totals retain all source years.
Dense rank retains ties. Unknown generic models/makes stay in totals but cannot be
named winners; missing specific variants can contribute to known generic models.
Unresolved counts in an eligible comparison withhold exact rankings for that group.

## Validation and exports

Build and test ingestion/staging/intermediate/marts first. Only on success does
the runner build nine export models and compare every exported row with reporting
tables. The custom export_file materialization writes CSV headers, JSON arrays,
or Parquet, and creates lightweight views over reporting models. Empty exports
contain no fake records. Views are database dependencies, not file-reader views.

External filenames remain annual_model_registrations.*, annual_model_rankings.*,
and annual_best_models.* for compatibility, despite the new rpt_ model names.
The runner writes a fresh batch under ../exports, validates all nine files, writes
_SUCCESS.json, then atomically updates latest.json. Consumers follow latest.json.
Failure leaves the previous successful batch pointer unchanged. Database models
are not one transaction spanning the project. Keep runs sequential.

There are 25 data checks for headers, duplicates, value preservation, null-preserving
cell counts, integer statuses, source/count reconciliation, dimensions/facts,
annual totals, year coverage, ranking, and ties. Fixture checks also cover
null/symbol cells, incomplete rankings, empty exports, and invalid-count rejection.
The snapshot contains 63,715 categories × 48 quarters = 3,058,320 long rows.
Logs/results are in logs/ and target/. Configuration vars control source_csv_path,
ranking_years, and export_dir; VEHICLE_DB_PATH overrides the database path.

Keep this README, ../vehicle_pipeline_design.md, ../duckdb/README.md, and the root
README consistent whenever dbt/SQL logic changes. AGENTS.md records this rule.


## Verified naming migration — 6 October 2026

The production database has been migrated successfully. All 25 data checks passed,
and all nine exports were independently verified against the reporting tables.
Old and new table contents were compared before the nine old project tables and
nine old export views were retired; only source_file/loaded_at run metadata was
excluded from table comparison. The empty src/cln/int/drv schemas were removed.

The new schemas are raw, staging, intermediate, core, reporting, and vehicle_export.
The fixed recovered CSV is retained in dbt/data. Business results and external export
filenames remain unchanged. Use run_pipeline.py for normal future builds.


## Custom export settings and dbt configuration validation

Custom materialization settings belong in the supported `meta` configuration,
not as additional top-level config keys. Export models use:

```sql
{{ config(meta={'export': {
    'file_format': 'csv',
    'output_name': 'annual_best_models'
}}) }}
```

The export_file materialization reads `config.get('meta', {}).get('export', {})`
and retrieves file_format/output_name from that dictionary. This avoids the
UnusedConfigKey (dbt1060) diagnostic for output_name and keeps all nine export
models consistent. Filenames, report logic, and delivery formats remain unchanged.
See [dbt custom configuration guidance](https://docs.getdbt.com/reference/deprecations).


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
