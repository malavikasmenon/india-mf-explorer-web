# pipelines/nav_backfill.py

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from data_pipeline.clients.mfapi import fetch_history
from data_pipeline.storage.parquet import write_parquet
from data_pipeline.storage.paths import nav_month_path
from data_pipeline.storage.metadata import write_ingest_metadata

# Fetched and written in batches rather than all 14k schemes at once, so a
# run that dies partway (timeout, OOM, a cancelled Actions job) has already
# saved everything up to the last completed batch instead of losing all of
# it - the next run resumes from there instead of starting over.
BATCH_SIZE = 500

NAV_DIR = Path("data") / "nav"
FAILURES_PATH = Path("data") / "nav_backfill_failures.json"


def fetch_nav_history(scheme_code):
    return fetch_history(scheme_code)


def transform_nav_history(data):
    df = pd.DataFrame(data["data"])

    # scheme_code is an identifier, not a quantity - keep it a string so it
    # reads and joins the same way as every other code in the schemes table.
    df["scheme_code"] = str(data["meta"]["scheme_code"])

    # Stays datetime64 (not .dt.date) here so store_nav_backfill can still
    # group by .dt.year/.dt.month; it's narrowed to a plain date right before
    # writing, so Parquet gets DATE rather than TIMESTAMP.
    df["date"] = pd.to_datetime(
        df["date"],
        format="%d-%m-%Y",
    )

    df["nav"] = df["nav"].astype(float)

    return df


def process_scheme(scheme_code):
    # A run touches ~14k schemes over several minutes; a single timeout or
    # malformed response must not take the whole backfill down with it.
    try:
        data = fetch_nav_history(scheme_code)
        return transform_nav_history(data)
    except (requests.RequestException, KeyError, ValueError) as exc:
        print(f"  skipping {scheme_code}: {exc}")
        return None


def store_nav_backfill(df):
    """Write one batch's rows into their monthly files, merging with
    whatever's already there rather than overwriting it - each batch only
    covers a subset of schemes, and most months are touched by every batch,
    so a blind overwrite would erase the previous batches' rows for that
    month."""

    grouped = df.groupby(
        [
            df["date"].dt.year,
            df["date"].dt.month,
        ]
    )

    for (year, month), partition in grouped:
        partition = partition.copy()
        # Narrowed from datetime64 to plain date here, once grouping is done -
        # DATE, not TIMESTAMP, in the Parquet the browser reads.
        partition["date"] = partition["date"].dt.date

        path = nav_month_path(year, month)
        if path.exists():
            partition = pd.concat([pd.read_parquet(path), partition], ignore_index=True)
            partition = partition.drop_duplicates(subset=["scheme_code", "date"])

        write_parquet(
            partition.sort_values(["date", "scheme_code"]),
            path,
        )


def already_backfilled() -> set[str]:
    """Scheme codes already present in the nav table on disk, so a resumed
    run doesn't re-fetch (and re-hit mfapi.in for) schemes it already has."""
    if not NAV_DIR.exists():
        return set()
    codes: set[str] = set()
    for path in NAV_DIR.rglob("*.parquet"):
        codes.update(pd.read_parquet(path, columns=["scheme_code"])["scheme_code"].unique())
    return codes


def build_nav_backfill(scheme_codes):
    done = already_backfilled()
    todo = [c for c in scheme_codes if c not in done]
    print(f"{len(scheme_codes) - len(todo)} schemes already backfilled; fetching {len(todo)}")

    failures: list[str] = []

    for start in range(0, len(todo), BATCH_SIZE):
        batch = todo[start : start + BATCH_SIZE]

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(process_scheme, batch))

        dfs = [df for df in results if df is not None]
        failures.extend(code for code, df in zip(batch, results) if df is None)

        if dfs:
            store_nav_backfill(pd.concat(dfs, ignore_index=True))

        processed = min(start + BATCH_SIZE, len(todo))
        print(f"  {processed}/{len(todo)} schemes processed, {len(failures)} failed so far")

    if failures:
        FAILURES_PATH.write_text(
            json.dumps(
                {
                    "failed_scheme_codes": failures,
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            )
        )
        print(f"{len(failures)} schemes had no usable NAV history; see {FAILURES_PATH}")
    elif FAILURES_PATH.exists():
        # A clean run after a previously-failing one - the old file would
        # otherwise sit there claiming failures that no longer exist.
        FAILURES_PATH.unlink()

    write_ingest_metadata(
        "nav",
        {
            "name": "mfapi",
            "url": "https://api.mfapi.in",
            "endpoints": [
                "/mf/{scheme_code}",
            ],
        },
    )