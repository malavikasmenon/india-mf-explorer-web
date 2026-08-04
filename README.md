# Open Indian Fund Data

Query Indian mutual fund data like a database. No ETL, no signup, no API keys.

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
  runs. The SQL is always visible; it's a drafting assistant, not an oracle (TBD)


## Data

Sourced from [AMFI](https://www.amfiindia.com/), which publishes NAV data daily
under SEBI's disclosure mandate and 
[mfapi.in](https://www.mfapi.in/)**, a mirror of AMFI's own scheme codes.


## Not financial advice

This is a data tool. It describes what funds hold and what they have returned,
and shows where every number came from. It does not recommend investments.
