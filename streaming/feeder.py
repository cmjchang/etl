"""Atomically publish prepared Parquet files to the Structured Streaming input."""

from __future__ import annotations

import argparse
import os
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKLOG = ROOT / "stream_backlog"
INPUT = ROOT / "stream_input"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-delay", type=float, default=1.0)
    parser.add_argument("--max-delay", type=float, default=5.0)
    parser.add_argument(
        "--seed", type=int, help="Set a repeatable delay sequence for practice."
    )
    args = parser.parse_args()
    if args.min_delay < 0 or args.max_delay < args.min_delay:
        parser.error("delay bounds must be nonnegative and max-delay >= min-delay")
    return args


def main() -> int:
    args = _parse_args()
    randomizer = random.Random(args.seed)
    if not BACKLOG.is_dir():
        print(f"Backlog folder not found: {BACKLOG}", file=sys.stderr)
        return 1
    INPUT.mkdir(parents=True, exist_ok=True)
    chunks = sorted(BACKLOG.glob("batch_*.parquet"))
    if not chunks:
        print(f"No Parquet chunks found in {BACKLOG}", file=sys.stderr)
        return 1

    for index, source in enumerate(chunks, start=1):
        destination = INPUT / source.name
        if destination.exists():
            print(
                f"Refusing to overwrite existing input file: {destination}",
                file=sys.stderr,
            )
            return 1

        temporary_path: Path | None = None
        try:
            # Stage beside the final file so rename is atomic on the same filesystem.
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{source.name}.", suffix=".tmp", dir=INPUT
            )
            os.close(descriptor)
            temporary_path = Path(temporary_name)
            shutil.copy2(source, temporary_path)
            os.rename(temporary_path, destination)
            # Retain the backlog copy until the complete destination is visible.
            source.unlink()
        except Exception as error:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            print(f"Failed to publish {source.name}: {error}", file=sys.stderr)
            return 1

        print(f"Published {index}/{len(chunks)}: {destination.name}", flush=True)
        if index < len(chunks):
            time.sleep(randomizer.uniform(args.min_delay, args.max_delay))

    print(f"Feeder finished; published {len(chunks)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
