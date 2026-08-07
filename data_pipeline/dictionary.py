"""The hand-written half of the published data dictionary.

Types, row counts and file lists are measured from the Parquet at build time
(see manifest.py) and are never written here — anything in this module
that could go stale relative to the artefact is a bug. What lives here is the
prose a column's type cannot express: what the value means, which field of the
source file it came from, and what one row of the table represents.

A table or column absent from these dicts still reaches the browser with its
name and type. Prose is an enrichment, never a gate — that is what lets a new
table appear in the UI without touching either this file or the frontend.
"""

from __future__ import annotations

# `subtitle` is what the rail shows: one sentence on what the table is.
# `grain` stays in the published catalog for consumers reading the manifest
# directly, but is not rendered — for this table it just restates the subtitle.
# It earns its place on tables where the cut is not obvious from the name, like
# `nav` (one row per scheme per day) or holdings (scheme x security x month).
TABLES: dict[str, dict] = {
    "schemes": {
        "title": "Schemes",
        # One plain sentence saying what the table *is*, before the grain says
        # how it is cut. Someone landing here cold should not have to infer
        # "mutual fund" from a column list.
        "subtitle": "Every mutual fund scheme published by AMFI.",
        "grain": "One row per AMFI scheme code.",
        "description": (
            "The scheme dimension, as published by AMFI in NAVAll.txt. Every column is "
            "verbatim from the source — nothing is parsed out of the scheme name and "
            "nothing is computed. The fund house, type and category are carried by "
            "section headers in the source file rather than by the data rows, so each "
            "row here inherits whichever headers preceded it."
        ),
        # Published in the manifest so the UI can offer a way in without knowing
        # anything about this table. An empty page with a blinking cursor is the
        # most intimidating thing a query tool can show someone.
        "examples": [
            {
                "label": "Which fund houses run the most schemes?",
                "sql": (
                    "SELECT fund_house, count(*) AS scheme_count\n"
                    "FROM schemes\n"
                    "GROUP BY 1\n"
                    "ORDER BY scheme_count DESC"
                ),
            },
            {
                "label": "The biggest SEBI categories",
                "sql": (
                    "SELECT scheme_category, count(*) AS scheme_count\n"
                    "FROM schemes\n"
                    "WHERE scheme_type = 'Open Ended Schemes'\n"
                    "GROUP BY 1\n"
                    "ORDER BY scheme_count DESC\n"
                    "LIMIT 20"
                ),
            },
            {
                "label": "Every Parag Parikh fund",
                "sql": (
                    "SELECT scheme_code, scheme_name, scheme_category\n"
                    "FROM schemes\n"
                    "WHERE scheme_name ILIKE '%parag parikh%'\n"
                    "ORDER BY scheme_name"
                ),
            },
            {
                "label": "Direct vs Regular — how many of each",
                "sql": (
                    "-- Plan type is still fused into the name; this is the\n"
                    "-- string-matching phase 2 will replace with a real column.\n"
                    "SELECT\n"
                    "  CASE WHEN scheme_name ILIKE '%direct%' THEN 'Direct'\n"
                    "       WHEN scheme_name ILIKE '%regular%' THEN 'Regular'\n"
                    "       ELSE 'unstated' END AS plan,\n"
                    "  count(*) AS scheme_count\n"
                    "FROM schemes\n"
                    "GROUP BY 1\n"
                    "ORDER BY scheme_count DESC"
                ),
            },
            {
                "label": "Schemes AMFI published with no ISIN at all",
                "sql": (
                    "SELECT fund_house, scheme_name\n"
                    "FROM schemes\n"
                    "WHERE isin_div_payout_growth IS NULL\n"
                    "  AND isin_div_reinvestment IS NULL\n"
                    "ORDER BY fund_house, scheme_name"
                ),
            },
        ],
    },
    "nav": {
        "title": "NAV",
        "subtitle": "Daily net asset value for every scheme, back to the 1990s.",
        "grain": "One row per scheme per day.",
        "description": (
            "The NAV fact table. One row for each day a scheme reported a value — there "
            "is no row for days it did not report, so gaps are weekends, holidays, and "
            "periods before launch or after wind-up rather than missing data. Where the "
            "source published a NAV that could not be read as a number, the row is kept "
            "with nav NULL: that a scheme published something broken on a given day is "
            "itself a fact about the source. Join to schemes on scheme_code.\n\n"
            "Sourced from mfapi.in, which mirrors AMFI's scheme codes and serves each "
            "scheme's full history. AMFI publishes no working bulk history export, so "
            "these rows are one hop from the publisher rather than direct — unlike "
            "schemes, which comes straight from AMFI's NAVAll.txt. Rows added daily "
            "from that same AMFI file are first-party."
        ),
        "examples": [],
    },
    "aum": {
        "title": "AUM",
        "subtitle": "Average assets under management for every scheme, by quarter.",
        "grain": "One row per scheme per quarter.",
        "description": (
            "Scheme-wise Average AUM (AAUM), as AMFI publishes it each quarter. Figures "
            "are in Rs Lakhs, exactly as published - not converted to rupees or crores. "
            "AMFI's own field names call this 'for the month', but the figure is the "
            "quarter's average, not a monthly one. period is kept verbatim as AMFI prints "
            "it (e.g. 'April - June 2026') rather than parsed into dates. Join to schemes "
            "on scheme_code - though unlike nav, that join is not guaranteed to match: "
            "schemes is a current snapshot of NAVAll.txt, so a scheme that closed or "
            "matured after the quarter a row covers can appear here with no corresponding "
            "row in schemes."
        ),
        "examples": [],
    },
}

# Declared nullability, mirroring the CREATE TABLE in build_schemes.py. It is stated
# here rather than read from the Parquet because Parquet has no NOT NULL: every
# column comes back from DESCRIBE as nullable regardless of what the pipeline
# proved before writing it. Same reason the constraints are asserted in the
# pipeline at all — see build_schemes.py's SCHEMA comment.
NOT_NULL: dict[str, set[str]] = {
    "schemes": {"scheme_code", "scheme_name", "fund_house", "scheme_type", "scheme_category"},
    # nav is deliberately absent from this set: a row whose NAV could not be
    # parsed is kept with NULL rather than dropped (see build_nav.py).
    "nav": {"scheme_code", "nav_date"},
    "aum": {
        "scheme_code",
        "period",
        "aum_excl_fof_domestic_incl_fof_overseas",
        "aum_fof_domestic",
    },
}

# The identifier, in order. Parquet cannot carry a primary key, so the catalog
# states it — it is the first thing anyone needs to know to join two tables, and
# the UI marks these columns so it is visible without reading prose.
PRIMARY_KEY: dict[str, list[str]] = {
    "schemes": ["scheme_code"],
    "nav": ["scheme_code", "nav_date"],
    "aum": ["scheme_code", "period"],
}

COLUMNS: dict[str, dict[str, dict]] = {
    "schemes": {
        "scheme_code": {
            "description": "AMFI's scheme identifier, and the join key on every query.",
            "source_field": "NAVAll.txt field 1",
        },
        "isin_div_payout_growth": {
            "description": (
                "ISIN for the dividend-payout and growth variants — one field serving "
                "both, which is how AMFI publishes it. NULL where the source had '-'. "
                "A few rows carry junk instead of an ISIN ('Redeemed', 'HDFCNIVODG'); "
                "those are kept verbatim as evidence of what AMFI published."
            ),
            "source_field": "NAVAll.txt field 2 (ISIN Div Payout/ISIN Growth)",
        },
        "isin_div_reinvestment": {
            "description": (
                "ISIN for the dividend-reinvestment variant. NULL where the source had "
                "'-', which is most rows — reinvestment options are far less common."
            ),
            "source_field": "NAVAll.txt field 3",
        },
        "scheme_name": {
            "description": (
                "The full scheme name, exactly as published — including inconsistent "
                "spacing and casing. Plan (Direct/Regular) and option (Growth/IDCW) are "
                "buried in this string and are not yet parsed into their own columns; "
                "AMCs use no shared convention for where in the name they appear."
            ),
            "source_field": "NAVAll.txt field 4",
        },
        "fund_house": {
            "description": "The AMC. Carried by a bare header line in the source, not by the data row.",
            "source_field": "NAVAll.txt section header (AMC line)",
        },
        "scheme_type": {
            "description": (
                "Open Ended Schemes, Close Ended Schemes, or Interval Fund Schemes. "
                "From the section header, before the parenthesis."
            ),
            "source_field": "NAVAll.txt section header, before '('",
        },
        "scheme_category": {
            "description": (
                "SEBI scheme category, e.g. 'Equity Scheme - Large & Mid Cap Fund'. "
                "From the section header, inside the parentheses. Categories are "
                "restated by SEBI over time, so this is the category as of this "
                "snapshot rather than a stable historical label."
            ),
            "source_field": "NAVAll.txt section header, inside '(...)'",
        },
    },
    "nav": {
        "scheme_code": {
            "description": (
                "AMFI's scheme identifier, and the join key to schemes. Every value here "
                "is guaranteed to exist in schemes — the build fails rather than publish "
                "a NAV row that references a scheme the catalog does not have."
            ),
            "source_field": "mfapi scheme code (AMFI's own)",
        },
        "nav_date": {
            "description": (
                "The date the NAV applies to, not the date it was published. Dates are "
                "per row: there is simply no row for a day a scheme did not report."
            ),
            "source_field": "mfapi data[].date (DD-MM-YYYY)",
        },
        "nav": {
            "description": (
                "Net asset value per unit, in rupees. Total-return by construction — it "
                "absorbs distributions — so the ratio of two NAVs is the return between "
                "those dates, with no dividend adjustment needed. NULL where the source "
                "published a value that could not be read as a number; the row is kept "
                "so that fact stays visible."
            ),
            "source_field": "mfapi data[].nav",
        },
    },
    "aum": {
        "scheme_code": {
            "description": "AMFI's scheme identifier, and the join key to schemes.",
            "source_field": "average-aum-schemewise AMFI_Code",
        },
        "period": {
            "description": (
                "The quarter this figure averages over, exactly as AMFI prints it "
                "(e.g. 'April - June 2026') - not parsed into a date."
            ),
            "source_field": "average-aum-schemewise period",
        },
        "aum_excl_fof_domestic_incl_fof_overseas": {
            "description": (
                "Average AUM for the quarter, Rs Lakhs. Excludes domestic fund-of-funds "
                "assets but includes overseas fund-of-funds assets, per AMFI's own split."
            ),
            "source_field": "average-aum-schemewise AverageAumForTheMonth.ExcludingFundOfFundsDomesticButIncludingFundOfFundsOverseas",
        },
        "aum_fof_domestic": {
            "description": "Average AUM for the quarter from domestic fund-of-funds assets, Rs Lakhs.",
            "source_field": "average-aum-schemewise AverageAumForTheMonth.FundOfFundsDomestic",
        },
    },
}
