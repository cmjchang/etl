# DuckDB / dbt general SQL logic

Updated: 6 October 2026.

The authoritative pipeline is ../dbt/run_pipeline.py, using ../my_database.duckdb.
The fixed CSV in dbt/data was recovered from the existing raw database snapshot.
The prior external duckdb folder was absent when this rename began.

| Layer | Physical schema | Main models |
|---|---|---|
| Ingestion / sources | raw | raw_dvla__vehicle_registrations |
| Staging | staging | stg_dvla__vehicle_registrations |
| Intermediate | intermediate | int_vehicle_registrations__unpivoted |
| Core marts | core | dim_vehicle, dim_quarter, fct_vehicle_registrations |
| Reporting marts | reporting | rpt_annual_model_registrations, rpt_annual_model_rankings, rpt_annual_best_models |

Staging uses source('dvla', 'vehicle_registrations'), with an explicit dependency
on the ingestion model. Later models use ref(). BodyType becomes body_type;
Make -> make, GenModel -> generic_model, Model -> model, Fuel -> fuel_type.
Wide quarter names become registrations_YYYY_qN. Intermediate unpivots only quarter
columns with INCLUDE NULLS, then cleans labels and parses nonnegative integer counts.
Missing/suppressed values retain statuses and never become zero silently.

Core facts/dimensions preserve vehicle-quarter grain. Reporting ranks generic models
within body type in 2024–2026, across variants and fuels. 2026 Q1–Q2 participates
with YTD coverage. Dense rank preserves ties; incomplete comparisons withhold exact
rankings. Tests protect counts, statuses, joins, annual totals, eligibility, and ties.

Export models use export_<report>__<format> names. Filenames remain the existing
annual_model_registrations.*, annual_model_rankings.*, annual_best_models.*.
CSV, JSON arrays, and Parquet are independently verified against reporting tables.
../exports/latest.json identifies the latest completed batch.

The earlier dvla_analysis.sql, ingestion.sql, and analytics.sql files were absent
when this rename began. They are not restored or required by dbt. This README
documents the general SQL logic; the dbt model graph is authoritative.

From ../dbt, run .\.venv\Scripts\python.exe .\run_pipeline.py.
Use migrate_model_names.py once to build/compare/retire old project names safely.
See ../vehicle_pipeline_design.md and ../dbt/README.md for full details.
Update all general logic Markdown files together with future dbt/SQL changes.


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
