"""Merge nav's Parquet files down to fewer, larger ones as they age out.

Two tiers, both re-run daily and both no-ops once nothing needs compacting:

  compact_nav()       one file per month, for the current year's closed
                       months (nav_daily only ever writes to the current
                       month, so anything before it is permanently closed).

  compact_nav_years()  one file per *year*, for years before the current
                       one - a whole past year's data doesn't change, so
                       there's no reason to keep it spread across 12 files.

Left alone, nav accumulates one new small file per day forever, and every
query against it pays a metadata round-trip per file even when most of the
data gets pruned away - see the query-latency investigation this followed.
Compacting keeps file count bounded to roughly one new file per year for
history plus, at most, one per month for the current year and one per day
for the current month, instead of growing by one file every single day.
"""

from datetime import date
from pathlib import Path

import pandas as pd

from data_pipeline.storage.parquet import write_parquet
from data_pipeline.storage.paths import nav_month_path, nav_year_path

NAV_DIR = Path("data") / "nav"


def _merge(files: list[Path], target: Path) -> int:
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df = df.drop_duplicates(subset=["scheme_code", "date"])
    df = df.sort_values(["date", "scheme_code"])

    # Read everything before deleting anything - target and source can be
    # the same path (history.parquet is itself one of the files being merged).
    for f in files:
        f.unlink()

    write_parquet(df, target)
    return len(df)


def compact_nav():
    if not NAV_DIR.exists():
        return

    today = date.today()

    for year_dir in sorted(NAV_DIR.glob("year=*")):
        year = int(year_dir.name.split("=")[1])
        if year != today.year:
            continue  # older years are compact_nav_years()'s job, not this one

        for month_dir in sorted(year_dir.glob("month=*")):
            month = int(month_dir.name.split("=")[1])
            if month == today.month:
                continue

            files = sorted(month_dir.glob("*.parquet"))
            if len(files) <= 1:
                continue

            rows = _merge(files, nav_month_path(year, month))
            print(f"  compacted {year}-{month:02d}: {len(files)} files -> 1 ({rows} rows)")


def compact_nav_years():
    if not NAV_DIR.exists():
        return

    today = date.today()

    for year_dir in sorted(NAV_DIR.glob("year=*")):
        year = int(year_dir.name.split("=")[1])
        if year >= today.year:
            continue  # this year stays at monthly granularity, for now

        files = sorted(year_dir.rglob("*.parquet"))
        if len(files) == 1 and files[0].parent == year_dir:
            continue  # already a single file directly under the year folder

        rows = _merge(files, nav_year_path(year))
        for month_dir in year_dir.glob("month=*"):
            month_dir.rmdir()  # now empty, its file was one of those just merged

        print(f"  compacted {year}: {len(files)} files -> 1 ({rows} rows)")
