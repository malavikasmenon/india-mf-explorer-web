from datetime import date

import pandas as pd

from data_pipeline.clients.amfi import fetch_ter_month
from data_pipeline.storage.metadata import write_ingest_metadata
from data_pipeline.storage.parquet import write_parquet
from data_pipeline.storage.paths import ter_partition_path


def fetch_ter():
    """This month's TER rows for every scheme - every day AMFI has
    published so far. Refetched from day one each run rather than just the
    newest day, because the source has no day-level filter (see
    clients/amfi.py's fetch_ter_month): getting today's row for every
    scheme costs the same full-month page-through as getting the whole
    month, so there is nothing to save by asking for less."""
    today = date.today()
    return fetch_ter_month(f"{today.month:02d}-{today.year}")


def transform_ter(rows):
    """AMFI has no AMFI_Code/scheme_code in this response at all - only
    NSDLSchemeCode, an identifier from a different registry than the one
    schemes/nav/aum share. Rather than guess a join via Scheme_Name, this
    table stands alone: scheme_name/type/category are kept here verbatim
    rather than looked up, since there is nothing reliable to look them up
    against."""
    df = pd.DataFrame(
        [
            {
                "nsdl_scheme_code": row["NSDLSchemeCode"],
                "scheme_name": row["Scheme_Name"],
                "scheme_type": row["SchemeType_Desc"],
                "scheme_category": row["SchemeCat_Desc"],
                "ter_date": pd.to_datetime(row["TER_Date"]).date(),
                "regular_ber": float(row["R_BER"]),
                "regular_brokerage_cost": float(row["R_BrokerageCost"]),
                "regular_transaction_cost": float(row["R_TransactionCost"]),
                "regular_statutory_levies": float(row["R_StatutoryLevies"]),
                "regular_ter": float(row["R_TER"]),
                "direct_ber": float(row["D_BER"]),
                "direct_brokerage_cost": float(row["D_BrokerageCost"]),
                "direct_transaction_cost": float(row["D_TransactionCost"]),
                "direct_statutory_levies": float(row["D_StatutoryLevies"]),
                "direct_ter": float(row["D_TER"]),
            }
            for row in rows
        ]
    )

    return df.drop_duplicates(subset=["nsdl_scheme_code", "ter_date"])


def store_ter(df):
    """One partition file per day, like nav - split out of the single
    month-wide fetch rather than written as one big file, so compaction
    (ter_compaction.py) can work on it the same way it works on nav."""
    for ter_date, partition in df.groupby("ter_date"):
        write_parquet(partition, ter_partition_path(ter_date))


def build_ter():
    rows = fetch_ter()
    df = transform_ter(rows)

    if len(df):
        store_ter(df)

    write_ingest_metadata(
        "ter",
        {
            "name": "AMFI",
            "url": "https://www.amfiindia.com/ter-of-mf-schemes",
            "endpoints": [
                "/api/populate-te-rdata-revised",
            ],
        },
    )
