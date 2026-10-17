"""Prepare online retail CSV data as typed, chronologically ordered Parquet files."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
DBT_PROJECT = ROOT
DATABASE = ROOT / "streaming.duckdb"
BACKLOG = ROOT / "stream_backlog"
INPUT = ROOT / "stream_input"
CHECKPOINT = ROOT / "stream_checkpoint"
QUARANTINE = ROOT / "quarantine"
MANIFEST = ROOT / ".prepared.json"
DEFAULT_SOURCE_URL = "https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/master/data/retail-data/all/online-retail-dataset.csv"
REMOTE_DATE_FORMAT = "%m/%d/%Y %H:%M"
REQUIRED_COLUMNS = (
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
)


def _ensure_output_paths_are_clear(reset: bool) -> None:
    if MANIFEST.exists() and not reset:
        raise FileExistsError(
            f"{MANIFEST.name} already exists. Use --reset only after stopping all "
            "streaming processes and clearing the backlog, input, checkpoint, and "
            "quarantine contents together."
        )

    for directory in (BACKLOG, INPUT, CHECKPOINT, QUARANTINE):
        if directory.exists() and any(directory.iterdir()):
            raise FileExistsError(
                f"{directory.name}/ is not empty. Stop all streaming processes and "
                "clear the backlog, input, checkpoint, and quarantine together before "
                "preparing a fresh replay. The script never deletes these paths."
            )


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _write_quarantine(
    connection: duckdb.DuckDBPyConnection,
    destination: Path,
) -> int:
    rejected_rows = connection.execute("""
        SELECT source_row, rejection_reasons,
               invoice_no_raw, stock_code_raw, description_raw, quantity_raw,
               invoice_date_raw, unit_price_raw, customer_id_raw, country_raw
        FROM intermediate.int_online_retail__rejected
        ORDER BY source_row
        """).fetchall()
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["source_row", "rejection_reasons", "raw_values"])
        for row in rejected_rows:
            writer.writerow(
                [
                    row[0],
                    row[1],
                    json.dumps(
                        dict(zip(REQUIRED_COLUMNS, row[2:])),
                        ensure_ascii=False,
                        default=str,
                    ),
                ]
            )
    return len(rejected_rows)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--source-csv",
        type=Path,
        help="Use an existing local CSV instead of the default remote dataset.",
    )
    source_group.add_argument(
        "--source-url",
        help="Read a raw CSV URL through DuckDB instead of the default Databricks sample.",
    )
    parser.add_argument(
        "--date-format",
        help=(
            "DuckDB strptime format for a custom --source-csv or --source-url. "
            "For example, '%%m/%%d/%%Y %%H:%%M'."
        ),
    )
    parser.add_argument("--rows-per-chunk", type=int, default=50)
    parser.add_argument(
        "--limit-rows",
        type=int,
        help="Process only the first N source records for a quick practice run.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Allow replacing the manifest after you manually clear all runtime data folders.",
    )
    args = parser.parse_args()
    if args.rows_per_chunk <= 0:
        parser.error("--rows-per-chunk must be a positive integer")
    if args.limit_rows is not None and args.limit_rows <= 0:
        parser.error("--limit-rows must be a positive integer")
    if args.source_csv and not args.date_format:
        parser.error("--date-format is required when --source-csv is supplied")
    if args.source_url and not args.date_format:
        parser.error("--date-format is required when --source-url is supplied")
    if args.date_format and not (args.source_csv or args.source_url):
        parser.error("--date-format is only valid with --source-csv or --source-url")
    return args


def _run_dbt(
    source_path: str,
    date_format: str,
    rows_per_chunk: int,
    limit_rows: int,
    target_path: Path,
) -> None:
    environment = os.environ.copy()
    environment["STREAMING_DB_PATH"] = str(DATABASE.resolve())
    variables = {
        "source_path": source_path,
        "date_format": date_format,
        "rows_per_chunk": rows_per_chunk,
        "limit_rows": limit_rows,
    }
    dbt_executable = shutil.which("dbt")
    if dbt_executable is None:
        raise RuntimeError(
            "dbt was not found; run this script inside the uv environment"
        )
    subprocess.run(
        [
            dbt_executable,
            "build",
            "--project-dir",
            str(DBT_PROJECT),
            "--profiles-dir",
            str(DBT_PROJECT),
            "--target-path",
            str(target_path),
            "--vars",
            json.dumps(variables),
        ],
        check=True,
        cwd=ROOT,
        env=environment,
    )


def main() -> int:
    args = _parse_args()
    try:
        _ensure_output_paths_are_clear(args.reset)
        if args.source_csv:
            source_path = str(args.source_csv.expanduser().resolve())
            date_format = args.date_format
            if not Path(source_path).is_file():
                raise FileNotFoundError(f"CSV file does not exist: {source_path}")
        elif args.source_url:
            source_path = args.source_url
            date_format = args.date_format
        else:
            source_path = DEFAULT_SOURCE_URL
            date_format = REMOTE_DATE_FORMAT

        ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".prep-", dir=ROOT) as temporary_root:
            temporary_root_path = Path(temporary_root)
            backlog_staging = temporary_root_path / "stream_backlog"
            quarantine_staging = temporary_root_path / "quarantine"
            partitioned_export = temporary_root_path / "partitioned_export"
            backlog_staging.mkdir()
            quarantine_staging.mkdir()

            _run_dbt(
                source_path,
                date_format,
                args.rows_per_chunk,
                args.limit_rows or 0,
                temporary_root_path / "dbt_target",
            )

            connection = duckdb.connect(str(DATABASE))
            try:
                input_count = connection.execute(
                    "SELECT count(*) FROM raw.raw_online_retail__transactions"
                ).fetchone()[0]
                accepted_count = connection.execute(
                    "SELECT count(*) FROM intermediate.int_online_retail__accepted"
                ).fetchone()[0]
                rejected_count = connection.execute(
                    "SELECT count(*) FROM intermediate.int_online_retail__rejected"
                ).fetchone()[0]
                if accepted_count + rejected_count != input_count:
                    raise RuntimeError(
                        "dbt model reconciliation failed: "
                        f"accepted={accepted_count}, rejected={rejected_count}, "
                        f"input={input_count}. No Parquet backlog was published."
                    )

                _write_quarantine(
                    connection, quarantine_staging / "rejected_records.csv"
                )
                chunk_count = connection.execute("""
                    SELECT coalesce(max(batch_id) + 1, 0)
                    FROM intermediate.int_online_retail__accepted
                    """).fetchone()[0]

                if chunk_count:
                    connection.execute("SET threads = 1")
                    copy_sql = (
                        "COPY (SELECT invoice_no, stock_code, description, quantity, "
                        "invoice_date, unit_price, customer_id, country, batch_id "
                        "FROM intermediate.int_online_retail__accepted "
                        "ORDER BY batch_id, invoice_date, source_row) "
                        f"TO {_sql_string(str(partitioned_export))} "
                        "(FORMAT PARQUET, COMPRESSION ZSTD, PARTITION_BY (batch_id), "
                        "FILENAME_PATTERN 'batch_{i}')"
                    )
                    connection.execute(copy_sql)
                    for partition in partitioned_export.glob("batch_id=*"):
                        batch_id = int(partition.name.split("=", 1)[1])
                        partition_files = list(partition.glob("*.parquet"))
                        if len(partition_files) != 1:
                            raise RuntimeError(
                                f"Expected one Parquet file for batch {batch_id}, "
                                f"found {len(partition_files)}"
                            )
                        destination = backlog_staging / f"batch_{batch_id:08d}.parquet"
                        os.replace(partition_files[0], destination)

                    published_batches = {
                        int(path.stem.removeprefix("batch_"))
                        for path in backlog_staging.glob("batch_*.parquet")
                    }
                    if published_batches != set(range(chunk_count)):
                        raise RuntimeError(
                            "Partitioned Parquet export did not produce every batch: "
                            f"expected {chunk_count}, found {len(published_batches)}"
                        )

                exported_count = connection.execute(
                    "SELECT count(*) FROM intermediate.int_online_retail__accepted"
                ).fetchone()[0]
                if exported_count != accepted_count:
                    raise RuntimeError(
                        f"Export row reconciliation failed: {exported_count} != {accepted_count}"
                    )
            finally:
                connection.close()

            for destination in (BACKLOG, QUARANTINE):
                if destination.exists():
                    destination.rmdir()
            os.rename(backlog_staging, BACKLOG)
            os.rename(quarantine_staging, QUARANTINE)

        manifest = {
            "source": source_path,
            "date_format": date_format,
            "rows_per_chunk": args.rows_per_chunk,
            "input_records": input_count,
            "accepted_records": accepted_count,
            "rejected_records": rejected_count,
            "exported_rows": exported_count,
            "chunk_count": chunk_count,
        }
        temporary_manifest = MANIFEST.with_suffix(".json.tmp")
        temporary_manifest.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary_manifest, MANIFEST)
        print(json.dumps(manifest, indent=2))
        print(f"Quarantine details: {QUARANTINE / 'rejected_records.csv'}")
        return 0
    except Exception as error:
        print(f"Preparation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
