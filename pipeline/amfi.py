"""Fetch and parse AMFI's NAVAll.txt.

The file is hierarchical rather than tabular. Section headers carry the
dimensional data — fund house, scheme type, scheme category — and each data row
inherits whichever headers most recently preceded it. See DESIGN.md 5.1-5.2.

It carries two things: the scheme dimension (`parse_navall`) and each scheme's
latest known NAV (`parse_navall_nav`). It is the source for `schemes`, and the
daily-append source for `nav`.

⚠️ AMFI's bulk history export — `DownloadNAVHistoryReport_Po.aspx`, DESIGN.md
5.5 — is **not usable** and has no fetcher here. Re-verified 2026-08-03: every
GET returns the HTML form rather than data, the page's AMC dropdown renders with
no options, it exposes one date field rather than a range, and the URL it now
redirects to 404s. Historical NAV is backfilled from mfapi instead; see
pipeline/mfapi.py.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
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

_DATE_FORMAT = "%d-%b-%Y"


class ParseError(ValueError):
    """A source file did not match the documented shape."""


@dataclass(frozen=True, slots=True)
class Scheme:
    """One row of the `schemes` table. Every field is published by AMFI verbatim."""

    scheme_code: int
    isin_div_payout_growth: str | None
    isin_div_reinvestment: str | None
    scheme_name: str
    fund_house: str
    scheme_type: str
    scheme_category: str


@dataclass(frozen=True, slots=True)
class NavRow:
    """One row of the `nav` table. See DESIGN.md 4."""

    scheme_code: int
    nav_date: date
    nav: Decimal | None


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


def parse_nav_value(value: str) -> Decimal | None:
    """Parse a NAV, or return None if the source published something unusable.

    Absence is "-" in NAVAll.txt and "" elsewhere; "N.A." also appears. Anything
    unparseable becomes NULL and the row is kept, because dropping it would
    destroy the evidence that a broken NAV was published that day — the row's
    existence is itself a fact about the source (DESIGN.md 4).
    """
    if value in ("", _MISSING):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def parse_nav_date(value: str, fmt: str, *, where: str) -> date:
    """Parse a NAV date strictly. Unlike the NAV itself this may not be NULL —
    it is half the primary key, so a row we cannot date is a row we cannot
    place."""
    try:
        return datetime.strptime(value, fmt).date()
    except ValueError as exc:
        raise ParseError(f"{where}: unparseable date {value!r}") from exc


def parse_navall_nav(text: str, *, source: str = "<navall>") -> Iterator[NavRow]:
    """Yield one NavRow per data row of NAVAll.txt — the daily-append path.

    The same file `parse_navall` reads for the scheme dimension; this reads the
    two columns that one discards. Only lines containing ';' are considered:
    `nav` needs nothing from the section headers, so the header state machine —
    and with it the "IL&FS Mutual Fund (IDF)" landmine of 5.2 — does not apply.

    Note the dates here are per-row and many are years old (5.3 — observed back
    to 2008), so the caller must decide which are in scope.
    """
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if ";" not in line or line.startswith(_COLUMN_HEADER):
            continue

        where = f"{source}:{lineno}"
        row = line.split(";")
        if len(row) != _EXPECTED_FIELDS:
            raise ParseError(
                f"{where}: expected {_EXPECTED_FIELDS} fields, got {len(row)}: {line!r}"
            )

        code = row[0].strip()
        try:
            scheme_code = int(code)
        except ValueError as exc:
            raise ParseError(f"{where}: non-integer scheme code {code!r}") from exc

        yield NavRow(
            scheme_code=scheme_code,
            nav_date=parse_nav_date(row[5].strip(), _DATE_FORMAT, where=where),
            nav=parse_nav_value(row[4].strip()),
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


_SNAPSHOT_RE = re.compile(r"NAVAll-(\d{8}T\d{6})Z\.txt$")


def snapshot_provenance(path: Path) -> dict:
    """Recover provenance for a snapshot already on disk.

    `fetch_navall` puts the retrieval time in the filename, so a rebuild from
    disk can publish the same provenance a fresh fetch would have. Dropping it
    would silently blank the "as of" date for data that is perfectly well dated.
    """
    match = _SNAPSHOT_RE.search(path.name)
    retrieved_at = (
        datetime.strptime(match.group(1), "%Y%m%dT%H%M%S")
        .replace(tzinfo=timezone.utc)
        .isoformat()
        if match
        else None
    )
    return {
        "source_url": NAVALL_URL,
        "retrieved_at": retrieved_at,
        "snapshot": path.name,
        "bytes": path.stat().st_size,
        "reused": True,
    }


def read_snapshot(path: Path) -> str:
    """Read a snapshot, stripping the BOM. Line endings are CRLF."""
    return path.read_text(encoding="utf-8-sig")


def scheme_dicts(schemes: Iterator[Scheme]) -> Iterator[dict]:
    return (asdict(s) for s in schemes)
