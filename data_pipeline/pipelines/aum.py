from datetime import date, datetime

import pandas as pd

from data_pipeline.clients.amfi import (
    fetch_average_aum_financial_years,
    fetch_average_aum_periods,
    fetch_average_aum_schemewise,
)
from data_pipeline.storage.metadata import write_ingest_metadata
from data_pipeline.storage.parquet import write_parquet
from data_pipeline.storage.paths import aum_partition_path


def _period_start(period: str) -> date:
    """"April - June 2026" -> 2026-04-01. Used only to name this quarter's
    partition file - the period itself is stored verbatim, not parsed, so
    this is not exposed as a column."""
    start_name, rest = period.split(" - ")
    year = int(rest.rsplit(" ", 1)[1])
    start_month = datetime.strptime(start_name.strip(), "%B").month
    return date(year, start_month, 1)


def fetch_aum():
    """The most recently published quarter - AMFI's own newest-first
    ordering on both the financial-year and period lists picks it out."""
    financial_years = fetch_average_aum_financial_years()
    fy_id = financial_years[0]["id"]

    periods = fetch_average_aum_periods(fy_id)
    period_id = periods[0]["id"]
    period = periods[0]["period"]

    groups = fetch_average_aum_schemewise(fy_id, period_id)
    return groups, period


def transform_aum(groups, period):
    """AMFI nests scheme rows under fund-house/scheme-type groups; flatten to
    one row per scheme. Fund house, scheme name and type are left out - they
    already live in schemes, joinable on scheme_code, and duplicating them
    here would just be a second copy to go stale against the source. period
    is kept as AMFI prints it ("April - June 2026") rather than parsed into
    dates - it is what AMFI actually published, and it is still the column
    that distinguishes one quarter's rows from another's once more than one
    quarter's file exists."""
    rows = [
        {
            "scheme_code": str(scheme["AMFI_Code"]),
            "period": period,
            "aum_excl_fof_domestic_incl_fof_overseas": float(
                aum["ExcludingFundOfFundsDomesticButIncludingFundOfFundsOverseas"]
            ),
            "aum_fof_domestic": float(aum["FundOfFundsDomestic"]),
        }
        for group in groups
        for scheme in group.get("schemes", [])
        for aum in [scheme["AverageAumForTheMonth"]]
    ]

    df = pd.DataFrame(rows)

    # Defensive, not observed: nothing here merges across fetches the way
    # nav_compaction/nav_backfill do, but if AMFI ever lists a scheme under
    # more than one group in a single response, this is what keeps
    # (scheme_code, period) the row's real key instead of just its intent.
    return df.drop_duplicates(subset=["scheme_code", "period"])


def store_aum(df, period):
    write_parquet(df, aum_partition_path(_period_start(period)))


def build_aum():
    groups, period = fetch_aum()
    df = transform_aum(groups, period)

    if len(df):
        store_aum(df, period)

    write_ingest_metadata(
        "aum",
        {
            "name": "AMFI",
            "url": "https://www.amfiindia.com/aum-data/average-aum",
            "endpoints": [
                "/api/average-aum-schemewise",
            ],
        },
    )
