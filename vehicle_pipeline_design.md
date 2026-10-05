# Vehicle registration pipeline: dbt / SQL logic

Updated: 5 October 2026. This document describes the implemented pipeline.

## Requirements and paths

- Static local snapshot; full rebuild; manual execution; no geography breakdown.
- Database: `C:\Users\Chiming\Documents\etl\my_database.duckdb`.
- dbt project: `C:\Users\Chiming\Documents\etl\dbt`.
- Input: `C:\Users\Chiming\Documents\etl\duckdb\output\df_VEH0160_UK.csv`.
- Output root: `C:\Users\Chiming\Documents\etl\exports`.
- Original `main.src_dvla` table and existing SQL scripts are preserved.
- Dependencies pinned: dbt Core 1.12.5, dbt-duckdb 1.11.0, DuckDB 1.5.5.

The input CSV was reconstructed once from the user's existing `dvla.parquet`.
It is not a fresh download and cannot recover text/symbols lost by prior conversion.
Each subsequent run reads this static CSV directly with `all_varchar=true`.

## Source and measure

Dataset: `df_VEH0160_UK`, UK first vehicle registrations, from 2014 Q3.
Fields: BodyType, Make, GenModel, Model, Fuel, and quarterly vehicle counts.
The inspected snapshot has 63,715 vehicle-category rows and 48 quarters ending at
2026 Q2. It has no duplicate source category keys. The long table has 3,058,320 rows.

[Government dataset and definitions](https://www.gov.uk/government/statistical-data-sets/vehicle-licensing-statistics-data-files).
[Supplied CSV URL](https://assets.publishing.service.gov.uk/media/6aad4b1ef1f8d2a39605fa1b/df_VEH0160_UK.csv).

The measure is `registration_count`: first registrations, used as a proxy for sales.
It is not a direct sales metric. Generic model groups specific model variants.
The source permits confidential `[c]` (1–4), unavailable `[x]`, and not applicable
`[z]` counts. Preserve markers instead of replacing them with zero.

## Layers: src → cln → int → drv → export

| Schema / folder | Models | Logic |
|---|---|---|
| `src` | `veh0160_raw` | Extract/load CSV; retain original headers and strings; add source_file/loaded_at |
| `cln` | `veh0160_columns` | Rename every field to a database-friendly snake_case name without changing values |
| `cln` | `vehicle_registrations` | Unpivot, clean labels, type quarter/count values, retain missing/status records |
| `int` | `dim_vehicle`, `dim_quarter`, `fct_vehicle_registrations` | Canonical dimensional model |
| `drv` | `annual_model_registrations`, `annual_model_rankings`, `annual_best_models` | Derived annual totals and rankings using int facts and dimensions |
| `vehicle_export` | Three format models for each drv table | Publish CSV, JSON arrays, and Parquet |

Source/clean/intermediate/derived folders match their physical database schemas.
There is one canonical copy of each fact/dimension in int; drv uses them to host
the derived analytics. It does not duplicate fact and dimension tables.
The schema naming macro uses exact names for this single local target.
All dependencies use dbt `ref()` rather than hard-coded schema references.
The export validator explicitly queries drv, because it runs outside dbt's SQL graph.

```text
CSV -> src.veh0160_raw
    -> cln.veh0160_columns
    -> cln.vehicle_registrations
    -> int.dim_vehicle + int.dim_quarter + int.fct_vehicle_registrations
    -> drv.annual_model_registrations
    -> drv.annual_model_rankings
    -> drv.annual_best_models
    -> vehicle_export views + validated local files
```

## Column renaming and cleaning

| Original header | cln wide header |
|---|---|
| BodyType | body_type |
| Make | make |
| GenModel | generic_model |
| Model | model |
| Fuel | fuel_type |
| 2026 Q2 | registrations_2026_q2 |

Quarter aliases are generated from headers matching `YYYY Q1` through `YYYY Q4`.
Reject unexpected headers and missing required descriptive fields.
Column renaming is a separate value-preserving model with a reconciliation test.

Unpivot only fields matching `^registrations_[0-9]{4}_q[1-4]$`, with
`UNPIVOT INCLUDE NULLS`. Metadata does not become a count, and blanks do not
disappear. Recover the original `period_label`, e.g. `2026 Q2`, from each alias.

Trim outer whitespace and use UNKNOWN for blank descriptive labels. Preserve
original values in src and the renamed wide cln table. Flag unknown make, generic
model, and specific model independently. Do not guess corrections for fuel or merge
similar model spellings. Reject cleaning collisions through key uniqueness tests.

Count statuses are `reported`, `confidential`, `unavailable`, `not_applicable`,
`missing`, or `invalid`. Only nonnegative integers fitting BIGINT are reported.
Invalid values fail validation. Valid zero stays zero; markers and blanks have null
registration_count and retain their status.

## Intermediate fact and dimensions

- `int.dim_vehicle`: one row per cleaned `(body_type, make, generic_model, model,
  fuel_type)` tuple, with identity flags. A deterministic hash of a JSON-encoded
  tuple supplies vehicle_key. Test uniqueness, including hash/cleaning collisions.
- `int.dim_quarter`: one row per source quarter with year, quarter number,
  quarter start/end, and actual quarter coverage for the year.
- `int.fct_vehicle_registrations`: one row per `(vehicle_key, quarter_key)`, with
  nullable registration_count and count_status. All keys must match dimensions.

## Derived analytics and winners

Group by `(year, body_type, make, generic_model)` and sum across variants and fuels.
Rank generic models separately within each body type. Requested years are
2024, 2025, and 2026, set by `ranking_years` in dbt_project.yml.
Annual totals retain all source years; rankings/winners use configured years.

Use all quarters available in the year. 2024 and 2025 cover Q1–Q4; 2026 covers
Q1–Q2 and remains eligible as year to date. Do not extrapolate or compare YTD counts
with full-year counts as if their periods matched. Partial calendar coverage is
metadata, never a reason to exclude a year from winners.

Use DENSE_RANK by descending annual_registration_count within year/body_type.
Keep all tied rank-1 models. Unknown makes/generic models remain in totals but do
not enter named-model rankings; missing specific variants can contribute to a known
generic model. Eligibility filtering happens before ranking.

`known_registration_count` sums numeric cells. `annual_registration_count` is null
when any relevant available-quarter cell is unresolved. If an otherwise eligible
model has unresolved counts, withhold exact rankings for that year/body-type
comparison. This conservative quality policy is separate from partial-year coverage.

Derived tables expose quarter coverage, full-year/YTD/partial-year labels, count
completeness, unknown identity flags, ranking eligibility/status, and rank where applicable.

## Validation and failure handling

The following checks run with the transformation build:

- Source headers, nonempty input, and unique source vehicle tuples.
- Exact src-to-cln column/value preservation.
- Null-preserving unpivot cell count: source rows × quarter columns.
- Unique cleaned vehicle-quarter grain, valid statuses, and integer count integrity.
- Per-quarter numeric totals and marker/missing-cell reconciliation.
- Unique dimensions, fact relationships, and fact row/total preservation.
- Annual group uniqueness and total reconciliation.
- Requested year presence and contiguous quarter coverage.
- Ranking eligibility, ordering, and all tied winners.

Errors block publication. Legitimate unresolved values are reported as warnings;
they remain present in totals and may withhold exact winners as described above.
Every export is re-read and compared as a multiset with its drv table, normalizing
CSV/JSON inferred types to the drv schema. Empty JSON remains an empty array;
empty CSV/Parquet outputs contain no fake records.

Fixture checks have exercised variant/fuel aggregation, tied winners, 2026 YTD,
unknown identities, null/marker preservation, incomplete comparisons, empty exports,
and invalid-count rejection. Migration verification compares old and new model
results before retiring the project-owned old layer objects.

## Manual build and exports

```powershell
Set-Location 'C:\Users\Chiming\Documents\etl\dbt'
.\.venv\Scripts\python.exe .\run_pipeline.py
```

The runner uses the isolated project environment, builds/tests src/cln/int/drv,
then builds exports only if that phase succeeds. dbt build with all exports in
one phase would not provide a global test barrier across independent branches.

The custom `drv_file` materialization creates lightweight views over drv and writes
CSV with headers, JSON arrays, and typed Parquet. All three tables are exported in
all three formats: nine files. Facts/dimensions remain in int and are not exported
unless requested later.

```text
annual_model_registrations.csv / .json / .parquet
annual_model_rankings.csv / .json / .parquet
annual_best_models.csv / .json / .parquet
```

Exports go to a new timestamped batch directory. Only after parity checks pass does
the runner write `_SUCCESS.json` and atomically publish `exports/latest.json`.
Use that manifest to locate the latest completed batch. Old completed batches
remain available; this is delivery recovery, not source-release history.
Failed builds do not roll back the entire DuckDB database. A failed run leaves
the last completed batch pointer unchanged. Keep writers/runs sequential.

Configuration: profiles.yml points at ../my_database.duckdb; environment variable
VEHICLE_DB_PATH can override it. dbt vars control source_csv_path, ranking_years,
and export_dir. Logs/results are in dbt/logs and dbt/target.

## Documentation maintenance

Whenever the dbt layers or general SQL logic change, update this document,
`dbt/README.md`, and `duckdb/README.md` in the same change. The existing duckdb SQL
scripts are exploratory predecessors; dbt is the authoritative pipeline.
Do not run ingestion.sql to create the new layer graph: it rebuilds main.src_dvla
and uses session-only temporary analysis tables.


## Layer migration status and one-time command

The renamed code passed all 25 data checks using the real static CSV in a separate
validation database. Its nine exports exactly match the previous published results.
The production database migration is pending because a DuckDB CLI session has
`my_database.duckdb` open. Exit that session with `.quit` before running dbt.

For the one-time database migration:

```powershell
Set-Location 'C:\Users\Chiming\Documents\etl\dbt'
.\.venv\Scripts\python.exe .\migrate_layers.py
```

This rebuilds/tests the new layers, verifies and publishes the exports, compares
each old project table with its replacement (excluding loaded_at run metadata),
and only then retires the matching old tables in one transaction. A mismatch
keeps the old tables. Unrelated objects and main.src_dvla are preserved; no
CASCADE deletion is used. The cleanup's mismatch/rollback/preservation behavior
was verified in a separate fixture database.

After migration, use run_pipeline.py for normal rebuilds. The layer configuration
and Markdown files have already been updated; closing the CLI is required only
to apply the new schemas to the production database.
