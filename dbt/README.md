# Vehicle analytics dbt project

Local DuckDB database: `../my_database.duckdb`. Original `main.src_dvla` is preserved.
The project owns the `src`, `cln`, `int`, `drv`, and `vehicle_export` schemas.

## Setup

Run from this folder. Use this project's environment, not the global `dbt` executable (the parent project currently has unrelated dbt/Snowflake packages).

```powershell
uv venv .venv --python 3.12
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
# Only if the static CSV has not yet been prepared:
./.venv/Scripts/python.exe prepare_source.py
```

Input defaults to `../duckdb/output/df_VEH0160_UK.csv`. It is initially reconstructed from the user's existing `dvla.parquet`, without downloading or changing that snapshot. Prefer placing an original CSV at this path if exact source-text preservation is required. Reconstruction cannot recover symbols already lost in prior conversion. dbt subsequently reads the fixed CSV using `all_varchar=true`.

## Run everything

```powershell
./run_pipeline.ps1
```

This builds and tests src/cln/int/drv first. Only on success does it build the nine export models, verify their contents against drv, mark a new batch complete, and atomically update `../exports/latest.json`. A failure leaves the latest completed batch unchanged. Database models themselves are not one global transaction. Keep runs sequential.

Individual commands:

```powershell
./.venv/Scripts/dbt.exe debug --profiles-dir .
./.venv/Scripts/dbt.exe build --profiles-dir . --exclude tag:export
./.venv/Scripts/dbt.exe docs generate --profiles-dir .
```

Do not build export models directly before validating drv. The custom `drv_file` materialization writes CSV, JSON arrays, or Parquet and creates lightweight views referencing drv. It supports empty outputs without adding fake null rows. Views reference drv, not published files; consumers should use completed files via `latest.json`.

## Business rules

- Metric: first UK registrations, a proxy for sales.
- Rank generic models per body type and year, combining specific models and fuels.
- Ranking years: 2024, 2025, 2026, configurable in `dbt_project.yml`.
- 2026 Q1–Q2 participates as YTD; partial years are not excluded or extrapolated.
- Ties use dense rank and all tied winners are retained.
- Unknown generic models/makes stay in totals but cannot be named winners. Missing specific variants do not disqualify a known generic model.
- Null and `[c]`/`[x]`/`[z]` counts retain statuses. Unexpected values fail validation.
- Any unresolved count in a named-model comparison withholds its exact ranking; coverage alone does not.
- Raw labels remain in src. The cln layer trims outer whitespace and flags missing identities; it does not guess fuel corrections or merge spellings.

## Outputs

`annual_model_registrations` contains all years and quality/coverage flags.
`annual_model_rankings` and `annual_best_models` contain configured ranking years.
Each is exported as CSV, JSON, and Parquet: nine files per successful batch.

Full rebuilds are intentional for the static 63,715-row source. Unpivoting 48 quarters produces 3,058,320 records. Tests check duplicate grain, null preservation, count/status reconciliation, dimension relationships, annual totals, ranking years, and ties. Run logs and test results are in `logs/` and `target/`.

The installed versions are pinned in `requirements.txt`. Change the database using `VEHICLE_DB_PATH`, and source/ranking years using dbt variables. The schema-naming macro uses exact schema names for this single local project.


## Layer and column naming

The current physical schemas and model folders match:

| Layer | Models | Responsibility |
|---|---|---|
| `src` | `veh0160_raw` | Static CSV ingestion; original source headers/values |
| `cln` | `veh0160_columns`, `vehicle_registrations` | Snake_case aliases; null-preserving unpivot, cleaning, typed counts |
| `int` | `dim_vehicle`, `dim_quarter`, `fct_vehicle_registrations` | Canonical fact/dimension tables |
| `drv` | `annual_model_registrations`, `annual_model_rankings`, `annual_best_models` | Derived analytics from int facts and dimensions |
| `vehicle_export` | Nine format models | Views over drv and validated delivery files |

In cln, source aliases are `BodyType -> body_type`, `Make -> make`,
`GenModel -> generic_model`, `Model -> model`, and `Fuel -> fuel_type`.
Wide quarter headers become `registrations_2026_q2`, etc., so every cln column
uses database-friendly naming. The long table exposes `period_label`, `year`,
`quarter_number`, and `quarter_start_date` rather than one column per quarter.

Facts and dimensions live once in int. The drv analytics join these tables through
dbt `ref()`; drv does not hold duplicate copies of dimensions or the detailed fact.
Business rules, exports, and counts remain the same after the layer migration.

Use the full pipeline to include validation and publishing:

```powershell
.\.venv\Scripts\python.exe .\run_pipeline.py
```

Keep this README, `../vehicle_pipeline_design.md`, and `../duckdb/README.md`
updated whenever dbt layers or general SQL logic change.


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
