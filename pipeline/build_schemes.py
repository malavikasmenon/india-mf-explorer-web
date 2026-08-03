"""Build the `schemes` dimension table from a NAVAll.txt snapshot.

Parsing is done in Python because the source is stateful line-by-line; typing,
validation and output are done in DuckDB so the same SQL dialect runs here and
in the browser. See DESIGN.md 4 for the schema and 7 for the architecture.

    python -m pipeline.build_schemes                 # fetch a fresh snapshot
    python -m pipeline.build_schemes --raw path.txt  # reuse one already on disk
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from pipeline.amfi import (
    Scheme,
    fetch_navall,
    parse_navall,
    read_snapshot,
    snapshot_provenance,
)

# Mirrors DESIGN.md 4. The constraints are asserted here, in the pipeline,
# because Parquet carries no PK/FK — the browser gets flat columns and trusts
# that this step already proved them clean.
SCHEMA = """
CREATE TABLE schemes (
  scheme_code             INTEGER PRIMARY KEY,
  isin_div_payout_growth  VARCHAR,
  isin_div_reinvestment   VARCHAR,
  scheme_name             VARCHAR NOT NULL,
  fund_house              VARCHAR NOT NULL,
  scheme_type             VARCHAR NOT NULL,
  scheme_category         VARCHAR NOT NULL
)
"""

INSERT = "INSERT INTO schemes VALUES (?, ?, ?, ?, ?, ?, ?)"

# A blank string satisfies NOT NULL but is just as broken. Catch it here rather
# than discovering it as an empty facet in the UI.
BLANK_CHECK = """
SELECT count(*) FROM schemes
WHERE trim(scheme_name) = ''
   OR trim(fund_house) = ''
   OR trim(scheme_type) = ''
   OR trim(scheme_category) = ''
"""

SUMMARY = """
SELECT
  count(*)                        AS schemes,
  count(DISTINCT fund_house)      AS fund_houses,
  count(DISTINCT scheme_type)     AS scheme_types,
  count(DISTINCT scheme_category) AS categories,
  count(isin_div_payout_growth)   AS with_isin_payout_growth,
  count(isin_div_reinvestment)    AS with_isin_reinvestment
FROM schemes
"""

MIN_EXPECTED_SCHEMES = 10_000


class ValidationError(RuntimeError):
    """The built table failed a check that must hold before publishing."""


def build(schemes: list[Scheme], out_dir: Path) -> dict:
    """Load parsed schemes into DuckDB, validate, and write schemes.parquet."""
    con = duckdb.connect()
    con.execute(SCHEMA)
    con.executemany(
        INSERT,
        [
            (
                s.scheme_code,
                s.isin_div_payout_growth,
                s.isin_div_reinvestment,
                s.scheme_name,
                s.fund_house,
                s.scheme_type,
                s.scheme_category,
            )
            for s in schemes
        ],
    )

    (blanks,) = con.execute(BLANK_CHECK).fetchone()
    if blanks:
        raise ValidationError(f"{blanks} rows have a blank required field")

    columns = [d[0] for d in con.execute(SUMMARY).description]
    stats = dict(zip(columns, con.execute(SUMMARY).fetchone()))
    if stats["schemes"] < MIN_EXPECTED_SCHEMES:
        raise ValidationError(
            f"only {stats['schemes']} schemes parsed; expected at least "
            f"{MIN_EXPECTED_SCHEMES}. The source format may have changed."
        )

    # Sorted by the join key so row-group statistics can prune scans later.
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "schemes.parquet"
    con.execute(
        "COPY (SELECT * FROM schemes ORDER BY scheme_code) TO ? (FORMAT parquet, COMPRESSION zstd)",
        [str(out_path)],
    )
    con.close()

    stats["parquet_bytes"] = out_path.stat().st_size
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, help="use an existing snapshot instead of fetching")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("data"))
    args = parser.parse_args()

    if args.raw:
        snapshot = args.raw
        provenance = snapshot_provenance(snapshot)
        print(f"reusing snapshot {snapshot}")
    else:
        snapshot, provenance = fetch_navall(args.raw_dir)
        print(f"fetched {provenance['bytes']:,} bytes -> {snapshot}")

    schemes = list(parse_navall(read_snapshot(snapshot)))
    stats = build(schemes, args.out)

    manifest = args.out / "schemes.ingest.json"
    manifest.write_text(json.dumps({"source": provenance, "stats": stats}, indent=2) + "\n")

    print(f"\nschemes.parquet  {stats['parquet_bytes']:,} bytes")
    for key, value in stats.items():
        if key != "parquet_bytes":
            print(f"  {key:<24} {value:,}")
    print(f"\nprovenance -> {manifest}")


if __name__ == "__main__":
    main()
