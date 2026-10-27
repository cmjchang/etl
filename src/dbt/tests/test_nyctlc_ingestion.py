import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import duckdb
from jinja2 import Environment, StrictUndefined

PROJECT = Path(__file__).resolve().parents[1]
DATASETS = {
    "green": "raw_nyctlc__green_taxi_trip",
    "fhvhv": "raw_nyctlc__high_volume_for_hire_vehicle_trip",
    "yellow": "raw_nyctlc__yellow_taxi_trip",
}


PERIODS = [(2025, m) for m in range(1, 13)] + [(2026, m) for m in range(1, 8)]


def render_model(dataset, variables=None, loaded=None):
    def compiler_error(message):
        raise ValueError(message)

    environment = Environment(undefined=StrictUndefined, extensions=["jinja2.ext.do"])
    environment.globals.update(
        var=lambda name, default=None: (variables or {}).get(name, default),
        exceptions=SimpleNamespace(raise_compiler_error=compiler_error),
        execute=True,
        is_incremental=lambda: loaded is not None,
        this="raw.target",
        run_query=lambda sql: SimpleNamespace(rows=[(f,) for f in loaded or []]),
    )
    macro = (PROJECT / "macros/nyctlc_trip_ingestion.sql").read_text()
    model = (PROJECT / "models/ingestion" / (DATASETS[dataset] + ".sql")).read_text()
    return environment.from_string(macro + model).render()


class NyctlcIngestionTests(unittest.TestCase):
    def test_monthly_paths(self):
        for dataset in DATASETS:
            for end_month in (1, 7, 12):
                with self.subTest(dataset=dataset, end_month=end_month):
                    variables = (
                        {} if end_month == 7 else {"nyctlc_end_month": end_month}
                    )
                    sql = render_model(dataset, variables)
                    paths = re.findall(r"'(https://[^']+)'", sql)
                    self.assertEqual(
                        paths,
                        [
                            "https://d37ci6vzurychx.cloudfront.net/trip-data/"
                            f"{dataset}_tripdata_{year}-{month:02d}.parquet"
                            for year, last in ((2025, 12), (2026, end_month))
                            for month in range(1, last + 1)
                        ],
                    )

    def test_incremental_skips_loaded_files(self):
        base = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_"
        loaded = [f"{base}2025-{m:02d}.parquet" for m in range(1, 13)]
        sql = render_model("yellow", loaded=loaded)
        self.assertEqual(
            re.findall(r"'(https://[^']+)'", sql),
            [f"{base}2026-{m:02d}.parquet" for m in range(1, 8)],
        )

    def test_incremental_nothing_pending(self):
        base = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_"
        loaded = [f"{base}{y}-{m:02d}.parquet" for y, m in PERIODS]
        sql = render_model("yellow", loaded=loaded)
        self.assertNotIn("read_parquet", sql)
        self.assertIn("where false", sql)

    def test_invalid_end_month(self):
        for value in (0, 13, -1, "7", 7.5, True, None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "nyctlc_end_month"):
                    render_model("yellow", {"nyctlc_end_month": value})

    def test_monthly_union_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory, duckdb.connect() as connection:
            for dataset in DATASETS:
                sql = render_model(dataset)
                for index, (year, month) in enumerate(PERIODS, 1):
                    filename = f"{dataset}_tripdata_{year}-{month:02d}.parquet"
                    path = Path(directory) / filename
                    extra = ", 42 as extra_column" if index == len(PERIODS) else ""
                    connection.sql(f"select {index} as month{extra}").write_parquet(
                        str(path)
                    )
                    sql = sql.replace(
                        "https://d37ci6vzurychx.cloudfront.net/trip-data/" + filename,
                        path.as_posix(),
                    )
                result = connection.sql(sql).order("month")
                self.assertEqual(
                    result.columns,
                    ["month", "extra_column", "source_file", "loaded_at"],
                )
                rows = result.fetchall()
                self.assertEqual(
                    [row[0] for row in rows], list(range(1, len(PERIODS) + 1))
                )
                self.assertEqual(
                    [row[1] for row in rows], [None] * (len(PERIODS) - 1) + [42]
                )
                for (year, month), row in zip(PERIODS, rows):
                    self.assertEqual(
                        row[2],
                        str(
                            Path(directory)
                            / f"{dataset}_tripdata_{year}-{month:02d}.parquet"
                        ),
                    )
                    self.assertIsNotNone(row[3])

    def test_single_source_override(self):
        with tempfile.TemporaryDirectory() as directory, duckdb.connect() as connection:
            path = Path(directory) / "taxi's.parquet"
            connection.sql("select 1 as trip_id").write_parquet(str(path))
            for dataset in DATASETS:
                sql = render_model(dataset, {"source_csv_path": str(path)})
                row = connection.sql(sql).fetchone()
                self.assertEqual(row[:2], (1, str(path)))
                self.assertIsNotNone(row[2])

    def test_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as directory, duckdb.connect() as connection:
            sql = render_model(
                "yellow", {"source_csv_path": str(Path(directory) / "missing.parquet")}
            )
            with self.assertRaises(duckdb.IOException):
                connection.sql(sql).fetchall()


if __name__ == "__main__":
    unittest.main()
