"""Focused integration tests for the local streaming preparation and feeder."""

from __future__ import annotations

import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

import streaming.feeder as feeder
import streaming.prep_data as prep


class StreamingPracticeTests(unittest.TestCase):
    def test_prepare_quarantine_parquet_and_feeder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "sample.csv"
            with source.open("w", newline="", encoding="utf-8") as output:
                writer = csv.writer(output)
                writer.writerow(prep.REQUIRED_COLUMNS)
                writer.writerow(
                    ["3", "B", "third", "2", "12/1/2010 8:30", "1.2500", "3", "UK"]
                )
                writer.writerow(
                    ["1", "A", "first", "1", "12/1/2010 8:00", "2.0000", "1", "UK"]
                )
                writer.writerow(
                    [
                        "2",
                        "C",
                        "bad quantity",
                        "nope",
                        "12/1/2010 8:10",
                        "1.0000",
                        "2",
                        "UK",
                    ]
                )
                writer.writerow(
                    [
                        "4",
                        "D",
                        "return",
                        "-1",
                        "12/1/2010 8:15",
                        "0.5000",
                        "",
                        "UK",
                    ]
                )
                writer.writerow(["malformed", "short"])
                writer.writerow(
                    ["5", "E", "last", "4", "12/1/2010 9:00", "3.0000", "5", "UK"]
                )

            paths = {
                "ROOT": root,
                "DATABASE": root / "streaming.duckdb",
                "BACKLOG": root / "stream_backlog",
                "INPUT": root / "stream_input",
                "CHECKPOINT": root / "stream_checkpoint",
                "QUARANTINE": root / "quarantine",
                "MANIFEST": root / ".prepared.json",
            }
            arg_values = [
                "prep_data.py",
                "--source-csv",
                str(source),
                "--date-format",
                "%m/%d/%Y %H:%M",
                "--rows-per-chunk",
                "2",
            ]
            with patch.multiple(prep, **paths), patch.object(sys, "argv", arg_values):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(prep.main(), 0)

                manifest = json.loads(paths["MANIFEST"].read_text(encoding="utf-8"))
                self.assertEqual(
                    [
                        manifest[key]
                        for key in (
                            "input_records",
                            "accepted_records",
                            "rejected_records",
                            "exported_rows",
                            "chunk_count",
                        )
                    ],
                    [6, 4, 2, 4, 2],
                )
                backlog = paths["BACKLOG"]
                chunks = sorted(backlog.glob("batch_*.parquet"))
                with duckdb.connect() as connection:
                    ordered = connection.execute(
                        "SELECT invoice_no FROM read_parquet(?) ORDER BY invoice_date, invoice_no",
                        [[str(chunk) for chunk in chunks]],
                    ).fetchall()
                    schema = connection.execute(
                        "DESCRIBE SELECT * FROM read_parquet(?)", [str(chunks[0])]
                    ).fetchall()
                    chunk_ranges = [
                        connection.execute(
                            "SELECT count(*), min(invoice_date), max(invoice_date) "
                            "FROM read_parquet(?)",
                            [str(chunk)],
                        ).fetchone()
                        for chunk in chunks
                    ]
                self.assertEqual([row[0] for row in ordered], ["1", "4", "3", "5"])
                types = {row[0]: row[1] for row in schema}
                self.assertEqual(types["quantity"], "BIGINT")
                self.assertEqual(types["unit_price"], "DECIMAL(18,4)")
                self.assertNotIn("batch_id", types)
                self.assertEqual([chunk[0] for chunk in chunk_ranges], [2, 2])
                self.assertLessEqual(chunk_ranges[0][2], chunk_ranges[1][1])
                with (paths["QUARANTINE"] / "rejected_records.csv").open(
                    encoding="utf-8", newline=""
                ) as rejects_file:
                    rejects = list(csv.DictReader(rejects_file))
                self.assertEqual(len(rejects), 2)
                self.assertTrue(
                    any("Quantity" in row["rejection_reasons"] for row in rejects)
                )

                feeder_paths = {
                    "ROOT": root,
                    "BACKLOG": backlog,
                    "INPUT": paths["INPUT"],
                }
                feeder_args = ["feeder.py", "--min-delay", "0", "--max-delay", "0"]
                with (
                    patch.multiple(feeder, **feeder_paths),
                    patch.object(sys, "argv", feeder_args),
                ):
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(feeder.main(), 0)
                self.assertEqual(len(list(paths["INPUT"].glob("*.parquet"))), 2)
                self.assertEqual(list(backlog.glob("*.parquet")), [])

    def test_dbt_parser_failure_does_not_publish_partial_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "malformed.csv"
            source.write_text(
                ",".join(prep.REQUIRED_COLUMNS)
                + '\n"broken quote\nnext,record,also,consumed,here,by,parser,UK\n',
                encoding="utf-8",
            )
            paths = {
                "ROOT": root,
                "DATABASE": root / "streaming.duckdb",
                "BACKLOG": root / "stream_backlog",
                "INPUT": root / "stream_input",
                "CHECKPOINT": root / "stream_checkpoint",
                "QUARANTINE": root / "quarantine",
                "MANIFEST": root / ".prepared.json",
            }
            arguments = [
                "prep_data.py",
                "--source-csv",
                str(source),
                "--date-format",
                "%m/%d/%Y %H:%M",
            ]
            with patch.multiple(prep, **paths), patch.object(sys, "argv", arguments):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(prep.main(), 1)
            self.assertFalse(paths["BACKLOG"].exists())
            self.assertFalse(paths["MANIFEST"].exists())


if __name__ == "__main__":
    unittest.main()
