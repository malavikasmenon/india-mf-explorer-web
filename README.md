# Open Indian Fund Data

Query Indian mutual fund data like a database. No ETL, no signup, no API keys.

> **Status: early.** Nothing is deployed yet. See [DESIGN.md](DESIGN.md) for the
> full design brief.

---

## Why

All of this data is already public — SEBI mandates its disclosure and AMFI
publishes it daily. What doesn't exist is a version that's already parsed,
joined, documented, and queryable.

So everyone who wants to analyse Indian mutual funds writes the same scraper,
stands up the same database, and repeats the same four hours of plumbing in
private before they can ask their first question.

This skips that. The tables are already loaded and joined. You start at the query.

## What it will do

- **SQL directly in the browser** against the full dataset — DuckDB-WASM, so
  queries run on your machine, not a server
- **Plain-English questions** that generate SQL you can read and edit before it
  runs. The SQL is always visible; it's a drafting assistant, not an oracle
- **Provenance on every row** — which source file, published when, parsed how
- **Use it from your own tools** — point `duckdb`, pandas, or a notebook straight
  at the hosted Parquet, or download the whole thing

## Use it without this site

```python
import duckdb

duckdb.sql("""
  SELECT scheme_name, nav, nav_date
  FROM 'https://<host>/nav/2026-06.parquet' n
  JOIN 'https://<host>/schemes.parquet' s USING (scheme_code)
  WHERE s.scheme_category LIKE 'Equity%'
""").df()
```

## Data

Sourced from [AMFI](https://www.amfiindia.com/), which publishes NAV data daily
under SEBI's disclosure mandate. Every record carries the source file and
retrieval time it came from.

One exception, stated plainly: **historical NAV is backfilled from
[mfapi.in](https://www.mfapi.in/)**, a mirror of AMFI's own scheme codes. AMFI
publishes no working bulk history export — its download page returns its own
HTML form for every request ([DESIGN.md §5.5](DESIGN.md)) — so history is one hop
from the publisher. The scheme catalogue and each day's new NAV come straight
from AMFI's `NAVAll.txt`. The manifest says which is which per table.

Coverage — including **what's missing** — is published alongside the data.
Gaps are documented, not hidden.

## Scope

**Now** — schemes and daily NAV, exactly as published.

**Next** — plan/option parsing, so the four variants of a fund can be grouped;
derived statistics (rolling returns, drawdowns, category rankings); and the
Direct-vs-Regular comparison, which shows what distributor commission actually
costs on an otherwise identical portfolio.

**Later** — monthly portfolio holdings, for overlap and concentration analysis.

## Licence

- **Code** — TBD (MIT or Apache-2.0)
- **Data** — TBD (CC-BY-4.0)

See [DESIGN.md §6](DESIGN.md) for the upstream licensing position, which is
unresolved and must be settled before any data is published.

## Not financial advice

This is a data tool. It describes what funds hold and what they have returned,
and shows where every number came from. It does not recommend investments.
