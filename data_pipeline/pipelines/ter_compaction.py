"""Merge ter's Parquet files down to fewer, larger ones as they age out.

Same two-tier scheme as nav_compaction.py, for the same reason - see that
module for the full rationale. ter accumulates the same way nav does: one
new small file per day, left in place forever if nothing ever merges them.
"""

from datetime import date
from pathlib import Path

import pandas as pd

from data_pipeline.storage.parquet import write_parquet
from data_pipeline.storage.paths import ter_month_path, ter_year_path

TER_DIR = Path("data") / "ter"


def _merge(files: list[Path], target: Path) -> int:
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df = df.drop_duplicates(subset=["nsdl_scheme_code", "ter_date"])
    df = df.sort_values(["ter_date", "nsdl_scheme_code"])

    # Read everything before deleting anything - target and source can be
    # the same path (history.parquet is itself one of the files being merged).
    for f in files:
        f.unlink()

    write_parquet(df, target)
    return len(df)


def compact_ter():
    if not TER_DIR.exists():
        return

    today = date.today()

    for year_dir in sorted(TER_DIR.glob("year=*")):
        year = int(year_dir.name.split("=")[1])
        if year != today.year:
            continue  # older years are compact_ter_years()'s job, not this one

        for month_dir in sorted(year_dir.glob("month=*")):
            month = int(month_dir.name.split("=")[1])
            if month == today.month:
                continue

            files = sorted(month_dir.glob("*.parquet"))
            if len(files) <= 1:
                continue

            rows = _merge(files, ter_month_path(year, month))
            print(f"  compacted {year}-{month:02d}: {len(files)} files -> 1 ({rows} rows)")


def compact_ter_years():
    if not TER_DIR.exists():
        return

    today = date.today()

    for year_dir in sorted(TER_DIR.glob("year=*")):
        year = int(year_dir.name.split("=")[1])
        if year >= today.year:
            continue  # this year stays at monthly granularity, for now

        files = sorted(year_dir.rglob("*.parquet"))
        if len(files) == 1 and files[0].parent == year_dir:
            continue  # already a single file directly under the year folder

        rows = _merge(files, ter_year_path(year))
        for month_dir in year_dir.glob("month=*"):
            month_dir.rmdir()  # now empty, its file was one of those just merged

        print(f"  compacted {year}: {len(files)} files -> 1 ({rows} rows)")
