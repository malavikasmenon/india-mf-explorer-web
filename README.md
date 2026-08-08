# Open Indian Fund Data

Query Indian mutual fund data like a database. No ETL, no signup, no API keys.

## Why

All of this data is already public — SEBI mandates its disclosure and AMFI publishes it regularly.What doesn't exist is a version that's already parsed, joined, documented, and queryable.

So everyone who wants to analyse Indian mutual funds writes the same scraper, stands up the same database, and repeats the same four hours of plumbing in private before they can ask their first question.

This skips that. The tables are already created and data loaded. You start at the query.

## Who is it for

Tools like this already exist, but they're built for those within the finance industry - fund houses, brokers, and distributors. If you're a
technical, analytically-minded retail investor, there's currently no way to
run your own analysis on Indian mutual fund data unless you work in the
industry. This is for those (potential) investors — to remove one level of
gatekeeping, so you can come to your own conclusions.

## What it will do

- **SQL directly in the browser** against the full dataset — DuckDB-WASM, so
  queries run on your machine, not a server


## Data

All data for this tool is hosted publicly on this [repo](https://github.com/malavikasmenon/open-mf-data-india). The Github actions run at the set cadence to fetch the latest available data.

Any information regarding the available tables, their schema and the corresponding sources can be found [here.](https://indian-financial-data-explorer.netlify.app/dictionary/)


## Development

**Web app** (Vue + DuckDB-WASM):
```
cd web && npm install && npm run build && npm run preview
```

**Data pipeline** (Python, fetches and builds the parquet tables into `data/`):
```
pip install -r requirements.txt

# populate nav data
python scripts/run_historic_backfill.py   # one-time, full history
python scripts/run_daily.py               # day-to-day: schemes, nav, ter

# populate aum data
python scripts/run_weekly.py
```

## Not financial advice

This is a data tool. It describes what funds hold and what they have returned,
and shows the source of this data. It does not recommend investments.


