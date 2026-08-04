# pipelines/nav_backfill.py

from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

from data_pipeline.clients.mfapi import fetch_history
from data_pipeline.storage.parquet import write_parquet
from data_pipeline.storage.paths import nav_month_path
from data_pipeline.storage.metadata import write_ingest_metadata


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

        write_parquet(
            partition.sort_values(["date", "scheme_code"]),
            nav_month_path(year, month),
        )


def build_nav_backfill(scheme_codes):

    with ThreadPoolExecutor(max_workers=8) as executor:
        dfs = list(executor.map(process_scheme, scheme_codes))

    dfs = [df for df in dfs if df is not None]
    print(f"fetched {len(dfs)} of {len(scheme_codes)} schemes")

    nav_df = pd.concat(
        dfs,
        ignore_index=True,
    )

    store_nav_backfill(nav_df)
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