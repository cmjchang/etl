# Local PySpark Streaming Practice

This isolated exercise uses its own dbt project and DuckDB database to ingest and
prepare the Databricks Spark repository's Online Retail CSV. Python runs dbt and
publishes the prepared Parquet chunks; a feeder simulates arrivals, and PySpark
Structured Streaming aggregates them. The vehicle dbt project and
`my_database.duckdb` remain unchanged.

## Environment

From the repository root, install the project dependencies and check Java:

```sh
uv sync
java -version
```

PySpark 4.x requires Java 17 or newer. The raw dbt model reads the CSV directly
from
<https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/master/data/retail-data/all/online-retail-dataset.csv>.
DuckDB reads the source as strings; the staging model parses its
`InvoiceDate` format `%m/%d/%Y %H:%M`, casts numeric fields, and classifies invalid
records. Short rows are null-padded for classification. Invalid CSV quoting or a
structural parser error fails the dbt build rather than silently dropping input.

All default data and runtime paths are relative to this directory:

- `streaming.duckdb` (separate from the vehicle pipeline database)
- `stream_backlog/`, `stream_input/`, `stream_checkpoint/`, and `quarantine/`
- `dbt_project.yml`, `profiles.yml`, and `models/` (the standalone dbt project and its `raw`, `staging`, and `intermediate` models)

## Prepare Data

Run this from the repository root for a quick 500-row practice run. dbt reads the
remote CSV directly through DuckDB:

```sh
uv run python streaming/prep_data.py --limit-rows 500
```

`raw_online_retail__transactions` preserves the source fields and scan row number.
`stg_online_retail__transactions` performs typed validation. Intermediate models
separate accepted/rejected rows and assign chronological batch IDs. dbt runs model
tests before Python checks row-count reconciliation, writes rejected source rows
to `quarantine/`, and exports typed Parquet chunks. The default chunk size is 50.

To use a different raw CSV URL, dbt reads it directly; provide its DuckDB
`strptime` date format:

```sh
uv run python streaming/prep_data.py --source-url 'https://example.com/retail.csv' --date-format '%m/%d/%Y %H:%M' --limit-rows 500
```

To use a local CSV, dbt reads that file and requires its date format explicitly:

```sh
uv run python streaming/prep_data.py --source-csv /path/to/online_retail.csv --date-format '%m/%d/%Y %H:%M' --limit-rows 500
```

Omit `--limit-rows` to prepare the complete dataset. At 50 rows per file, the
full dataset produces roughly 10,800 chunks. Use `--rows-per-chunk N` to change
the chunk size.

## Run The Stream

Open three terminals at the repository root. Start the consumer first:

```sh
uv run python streaming/stream_consumer.py
```

Then start the feeder in a second terminal. It publishes one chunk at a time,
waiting a random 1–5 seconds between files:

```sh
uv run python streaming/feeder.py
```

Watch the consumer terminal for per-window revenue and quantity updates. The
feeder moves each source chunk only after an atomic rename publishes its complete
copy into `stream_input/`. The console sink is diagnostic; it is not a durable
results store.

## Verify And Restart

- Compare counts printed at preparation with `streaming/.prepared.json`; accepted
  plus rejected records must equal input records, and exported rows must equal
  accepted records.
- Run `uv run dbt test --project-dir streaming --profiles-dir streaming` with
  `STREAMING_DB_PATH` set to the absolute `streaming/streaming.duckdb` path to
  rerun dbt's model tests independently.
- Inspect `streaming/quarantine/rejected_records.csv` for source row numbers,
  available values, and rejection reasons.
- Chunk filenames are chronological. To inspect the Parquet contract, run
  `uv run python -c "import duckdb; print(duckdb.sql(\"DESCRIBE SELECT * FROM read_parquet('streaming/stream_backlog/batch_00000000.parquet')\").fetchall())"`.
- Stop and restart only the consumer while keeping `stream_input/` and
  `stream_checkpoint/` intact. Spark resumes from its checkpoint and does not
  reprocess files already recorded there.

## Fresh Replay

Stop the feeder and consumer first. A fresh replay requires deliberately clearing
all generated state together: `stream_backlog/`, `stream_input/`,
`stream_checkpoint/`, and `quarantine/`. From the repository root, remove only
those folders under `streaming/`, then prepare again with `--reset`:

```sh
rm -rf streaming/stream_backlog streaming/stream_input streaming/stream_checkpoint streaming/quarantine
uv run python streaming/prep_data.py --limit-rows 500 --reset
```

The script refuses to overwrite nonempty runtime folders and never deletes data
automatically. `--reset` allows replacing `.prepared.json`; the next run reads
the URL again and rebuilds the dbt tables in `streaming.duckdb`.

The two-hour watermark follows the maximum event timestamp observed, not feeder
wall-clock time. Chronological chunk ordering avoids advancing event time ahead
of the historical records; if out-of-order chunks are introduced, sufficiently
late events can be dropped from the aggregation state.