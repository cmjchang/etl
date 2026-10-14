Act as an expert Big Data engineer and PySpark architect. Please write a complete, production-grade, three-part Python local streaming practice environment using DuckDB, standard Python file operations, and PySpark Structured Streaming without Kafka or cloud services. 

Here are the precise specifications for the three scripts required:

1. Dataset Preparation & Chunker Script (`prep_data.py`):
- Use a dedicated practice directory (`./streaming/`) for scripts, source data, database, and runtime folders. Resolve default paths relative to that directory, not the terminal's current working directory.
- Connect to a separate `streaming.duckdb` database. Do not read or modify the existing vehicle pipeline's `my_database.duckdb`.
- Download the raw Online Retail CSV from `https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/master/data/retail-data/all/online-retail-dataset.csv` by default. Also accept a custom raw CSV URL or an existing local CSV through command-line options. Cache URL downloads atomically and validate the header before publishing; do not require an Excel workbook or Excel-reading dependency.
- Parse the default source's `InvoiceDate` with DuckDB format `%m/%d/%Y %H:%M`. For custom URLs and local CSV files, require an explicit date-format option rather than guessing ambiguous dates.
- Require the columns `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, and `Country`. Fail before exporting if required columns are missing or duplicated.
- Read CSV fields as strings before validation and assign an original source-row number before sorting. If using `ignore_errors=true`, also capture DuckDB CSV rejects; do not silently discard malformed rows.
- Quarantine recoverable malformed CSV records and records with invalid required values into `./quarantine/`, retaining available source values, source-row information, and rejection reasons. Report unrecoverable parser failures explicitly. Fail preparation if rejection capture or count reconciliation is incomplete.
- The raw CSV uses the source headers listed above, but accepted Parquet columns and the PySpark schema must use these matching snake_case names: `invoice_no`, `stock_code`, `description`, `quantity`, `invoice_date`, `unit_price`, `customer_id`, and `country`. Use strings for invoice/stock/description/customer/country fields, signed 64-bit integer for `quantity`, `DECIMAL(18,4)` for `unit_price`, and a timezone-naive timestamp for `invoice_date`.
- Reject invalid or overflowing numbers and timestamps, blank invoice/stock identifiers, and prices that cannot be represented exactly at the chosen scale. Retain negative quantities as returns and allow missing `customer_id` and `description`. Do not deduplicate or discard valid returns. Calculate revenue downstream using decimal arithmetic.
- Sort accepted rows by `invoice_date`, then original source-row number for deterministic ties. Use a window function to assign a zero-based `batch_id`, grouping every 50 accepted rows by default. Make rows per chunk configurable through a positive-integer command-line option.
- Export typed Parquet chunks into `./stream_backlog/` with zero-padded filenames such as `batch_00000000.parquet`. Keep `batch_id` and source-row metadata out of the exported business schema. Publish each completed file atomically; do not expose partial Parquet files.
- Report total input records, accepted records, rejected records, exported rows, and chunk count. Verify that accepted plus rejected equals total input records and that exported rows equals accepted records. A final chunk may contain fewer rows than the configured size.
- Refuse to overwrite an existing prepared dataset or nonempty backlog. Provide an explicit fresh-run reset option, but never reset automatically. Require all streaming processes to be stopped and the backlog, input directory, and checkpoint to be explicitly cleared together before rebuilding. Restrict reset to practice-owned paths and leave unrelated files untouched.

2. Real-Time Feeder Script (`feeder.py`):
- Scan the `./stream_backlog/` folder for the generated Parquet chunk files and feed them in ascending filename order to preserve chronological replay.
- Simulate a live stream by moving files one by one into an active `./stream_input/` folder.
- Implement an atomic move (write-then-rename) pattern: write/copy the file with a temporary `.tmp` extension into `./stream_input/`, then instantly use `os.rename()` to change it to `.parquet` so PySpark never reads partial or incomplete files.
- Use a hidden temporary filename in the destination directory, refuse destination filename collisions, and remove the backlog copy only after successful publication. The final rename must remain on the same filesystem.
- Introduce a randomized delay (`time.sleep` between 1 to 5 seconds) between each file transfer.
- Log progress clearly to the console.

3. PySpark Structured Streaming Consumer Script (`stream_consumer.py`):
- Initialize a local SparkSession configured with optimized local execution settings:
  - `.master("local[*]")`
  - `.config("spark.sql.shuffle.partitions", "4")` to avoid local thread overhead.
- Read the stream using `spark.readStream.format("parquet")` targeting `./stream_input/`.
- Supply an explicit schema matching the preparation script's snake_case Parquet columns, including `DecimalType(18, 4)` for `unit_price` and `LongType` for `quantity`. Configure the Spark session timezone consistently with the dataset's UK local-time interpretation (`Europe/London`).
- Configure streaming options:
  - `.option("maxFilesPerTrigger", "1")` to regulate micro-batch ingestion speed.
- Apply event-time streaming logic:
  - Apply a watermark on `invoice_date` (e.g., `withWatermark("invoice_date", "2 hours")`).
  - Perform a 10-minute sliding-window aggregation advancing every 5 minutes, calculating total revenue (`quantity * unit_price`) and total quantity grouped by `stock_code`.
  - Explain that watermark progress follows dataset event time, not the feeder's wall-clock delays, and that sufficiently late records may be dropped. Keep default file processing in arrival order; do not enable `latestFirst`.
- Set up mandatory fault tolerance using a local checkpoint directory (`./stream_checkpoint/`).
- Output the streaming results to the console using `.outputMode("update")` with a micro-batch trigger (`.trigger(processingTime='5 seconds')`).

Keep source ingestion, typed validation, rejection classification, chronological ordering, and batch assignment in a dedicated dbt project backed by `streaming.duckdb`, following the existing `raw_dvla__vehicle_registrations` pattern. Python should orchestrate dbt, reconcile model counts, write the rejected-model output to quarantine, and publish the batched model as Parquet. Do not modify the vehicle dbt project or `my_database.duckdb`.

Please provide concise instructions on dependencies managed with uv, the Java requirement for PySpark 4.x, directory setup, direct raw-CSV ingestion or supplying a local CSV, and running the pipeline concurrently in separate terminal windows. Start the consumer before the feeder. Include a small-subset practice run before processing the full dataset, which produces roughly 10,800 chunks at 50 rows per file.

Include focused verification steps for preparation counts, quarantine reasons, chronological chunk boundaries, Parquet schema compatibility, and consumer restart with the same checkpoint. Explain that console output is diagnostic rather than a durable results store, and that an ordinary restart preserves input files and checkpoints while a fresh replay requires the explicit coordinated reset described above. Keep the existing dbt workflow unchanged.