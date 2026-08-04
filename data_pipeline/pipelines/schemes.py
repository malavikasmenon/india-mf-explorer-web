import re

import pandas as pd

from data_pipeline.clients.amfi import fetch_navall
from data_pipeline.storage.metadata import write_ingest_metadata
from data_pipeline.storage.parquet import write_parquet
from data_pipeline.storage.paths import schemes_path

# A section header splits into type and category at the parenthesis:
#     Open Ended Schemes(Debt Scheme - Banking and PSU Fund)
# A parenthesis alone doesn't identify one, though - "IL&FS Mutual Fund (IDF)"
# is a fund house, not a section header. Every real scheme-type header ends in
# "Schemes"; no fund house does.
_SECTION_RE = re.compile(r"^(?P<type>.+?)\((?P<category>.+)\)$")
_COLUMN_HEADER = "Scheme Code"
_MISSING = "-"
_FIELDS = 6


def fetch_schemes():
    return fetch_navall()


def transform_schemes(text):
    """NAVAll.txt is hierarchical, not tabular: section headers carry the fund
    house, scheme type and category, and each data row inherits whichever
    headers most recently preceded it."""
    rows = []
    fund_house = scheme_type = scheme_category = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(_COLUMN_HEADER):
            continue

        if ";" not in line:
            match = _SECTION_RE.match(line)
            if match and match["type"].strip().endswith("Schemes"):
                scheme_type = match["type"].strip()
                scheme_category = match["category"].strip()
            else:
                fund_house = line
            continue

        fields = line.split(";")
        if len(fields) != _FIELDS or fund_house is None:
            continue

        code, isin_payout_growth, isin_reinvestment, name = (
            f.strip() for f in fields[:4]
        )
        if not code.isdigit():
            continue

        rows.append(
            {
                # An identifier, not a quantity - kept as a string like the
                # ISIN columns rather than a number nothing does arithmetic on.
                "scheme_code": code,
                "isin_div_payout_growth": None if isin_payout_growth == _MISSING else isin_payout_growth,
                "isin_div_reinvestment": None if isin_reinvestment == _MISSING else isin_reinvestment,
                "scheme_name": name,
                "fund_house": fund_house,
                "scheme_type": scheme_type,
                "scheme_category": scheme_category,
            }
        )

    return pd.DataFrame(rows)


def store_schemes(df):
    write_parquet(df, schemes_path())


def build_schemes():
    df = fetch_schemes()
    df = transform_schemes(df)
    store_schemes(df)
    write_ingest_metadata(
        "schemes",
        {
            "name": "AMFI",
            "url": "https://www.amfiindia.com/spages/NAVAll.txt",
        },
    )