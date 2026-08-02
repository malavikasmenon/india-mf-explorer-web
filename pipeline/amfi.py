"""Fetch and parse AMFI's NAVAll.txt.

The file is hierarchical rather than tabular. Section headers carry the
dimensional data — fund house, scheme type, scheme category — and each data row
inherits whichever headers most recently preceded it. See DESIGN.md 5.1-5.2.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

# www.amfiindia.com 302-redirects here; use the portal host directly.
NAVALL_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"

# A section header splits into type and category at the parenthesis:
#     Open Ended Schemes(Debt Scheme - Banking and PSU Fund)
# But a parenthesis alone does not identify one — "IL&FS Mutual Fund (IDF)" is a
# fund house. Every real scheme-type header ends in "Schemes"; no fund house
# does. Getting this wrong silently misattributes every row until the next AMC.
_SECTION_RE = re.compile(r"^(?P<type>.+?)\((?P<category>.+)\)$")

# AMFI's text-file convention for absence. Other junk values exist in the ISIN
# columns ("Redeemed", "HDFCNIVODG") and are kept verbatim — they are evidence
# of what AMFI published, and normalising them away destroys that.
_MISSING = "-"

_COLUMN_HEADER = "Scheme Code"
_EXPECTED_FIELDS = 6


class ParseError(ValueError):
    """NAVAll.txt did not match the documented shape."""


@dataclass(frozen=True, slots=True)
class Scheme:
    """One row of the `mf` table. Every field is published by AMFI verbatim."""

    scheme_code: int
    isin_div_payout_growth: str | None
    isin_div_reinvestment: str | None
    scheme_name: str
    fund_house: str
    scheme_type: str
    scheme_category: str


def parse_navall(text: str) -> Iterator[Scheme]:
    """Yield one Scheme per data row, resolving the hierarchy into flat rows.

    Raises ParseError rather than guessing when a line does not match the
    documented shape — a silent mis-parse here corrupts the dimension table for
    every downstream join.
    """
    fund_house: str | None = None
    scheme_type: str | None = None
    scheme_category: str | None = None

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()

        # Blank separators are a single space, not an empty string.
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
        if len(fields) != _EXPECTED_FIELDS:
            raise ParseError(
                f"line {lineno}: expected {_EXPECTED_FIELDS} fields, "
                f"got {len(fields)}: {line!r}"
            )
        if fund_house is None or scheme_type is None or scheme_category is None:
            raise ParseError(f"line {lineno}: data row before any section header")

        code, isin_payout_growth, isin_reinvestment, name = (
            f.strip() for f in fields[:4]
        )
        try:
            scheme_code = int(code)
        except ValueError as exc:
            raise ParseError(f"line {lineno}: non-integer scheme code {code!r}") from exc

        yield Scheme(
            scheme_code=scheme_code,
            isin_div_payout_growth=None if isin_payout_growth == _MISSING else isin_payout_growth,
            isin_div_reinvestment=None if isin_reinvestment == _MISSING else isin_reinvestment,
            scheme_name=name,
            fund_house=fund_house,
            scheme_type=scheme_type,
            scheme_category=scheme_category,
        )


def fetch_navall(raw_dir: Path, *, timeout: float = 120.0) -> tuple[Path, dict]:
    """Download NAVAll.txt to a timestamped snapshot. Returns (path, provenance)."""
    retrieved_at = datetime.now(timezone.utc)

    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        response = client.get(NAVALL_URL)
        response.raise_for_status()

    raw_dir.mkdir(parents=True, exist_ok=True)
    snapshot = raw_dir / f"NAVAll-{retrieved_at:%Y%m%dT%H%M%SZ}.txt"
    snapshot.write_bytes(response.content)

    provenance = {
        "source_url": NAVALL_URL,
        "retrieved_at": retrieved_at.isoformat(),
        "snapshot": snapshot.name,
        "bytes": len(response.content),
        "last_modified": response.headers.get("last-modified"),
    }
    return snapshot, provenance


def read_snapshot(path: Path) -> str:
    """Read a snapshot, stripping the BOM. Line endings are CRLF."""
    return path.read_text(encoding="utf-8-sig")


def scheme_dicts(schemes: Iterator[Scheme]) -> Iterator[dict]:
    return (asdict(s) for s in schemes)
