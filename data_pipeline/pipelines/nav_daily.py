from datetime import date

import pandas as pd

from data_pipeline.clients.mfapi import fetch_latest
from data_pipeline.storage.metadata import write_ingest_metadata
from data_pipeline.storage.parquet import write_parquet
from data_pipeline.storage.paths import nav_partition_path


def fetch_nav_daily():
    return fetch_latest()


def transform_nav_daily(data):
    df = pd.DataFrame(data)

    today = date.today().strftime("%d-%m-%Y")

    # mfapi's /mf/latest returns camelCase fields plus scheme metadata that
    # already lives in the schemes table; keep only what the nav table needs,
    # renamed to match nav_backfill's output so both land in the same schema.
    df = df.loc[df["date"] == today, ["schemeCode", "date", "nav"]].rename(
        columns={"schemeCode": "scheme_code"}
    )
    print(f"Fetched {len(df)} records for {today}")

    # scheme_code is an identifier, not a quantity - keep it a string so it
    # reads and joins the same way as every other code in the schemes table.
    df["scheme_code"] = df["scheme_code"].astype(str)

    # .dt.date (not pd.to_datetime's default) so this writes to Parquet as
    # DATE rather than TIMESTAMP - a NAV date has no time-of-day component,
    # and DuckDB-WASM's Arrow bindings only convert DATE columns to JS Date
    # objects automatically. A TIMESTAMP column arrives in the browser as a
    # raw epoch number instead.
    df["date"] = pd.to_datetime(
        df["date"],
        format="%d-%m-%Y",
    ).dt.date
    df["nav"] = df["nav"].astype(float)

    return df


def store_nav_daily(df):
    nav_date = df.iloc[0]["date"]
    write_parquet(
        df,
        nav_partition_path(nav_date),
    )


def build_nav_daily():
    data = fetch_nav_daily()
    df = transform_nav_daily(data)

    if len(df):
        store_nav_daily(df)

    
    write_ingest_metadata(
        "nav",
        {
            "name": "mfapi",
            "url": "https://api.mfapi.in",
            "endpoints": [
                "/mf/latest",
            ],
        },
    )