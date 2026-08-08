2 tables

<!-- Initial spec for Claude to collect data -->

1. schemes - use amfii navall.txt to get the info about all schemes 
2. nav daily - use mfapi /mf/latest endpoint. but to avoid dead schemes, just take the ones that has the date as the current day. this way you avoid adding funds that haven't been updated in a while
3. nav backfill - use all scheme codes from the schemes table and use mfapi /mf/{scheme_code} endpoint to populate the nav history. this might take some time, but since its a one time activity, it is fine

advantage of this design
1. for the schemes - we use the most reliable source 
2. for nav and backfill, we don't want to depend on our own parsing logic, lets use a tool that is already available and use that 

few points to note
1. i want to keep the data pipeline separate, ie first lets design how we are going to fetch and store the parquet files
2. i dont want the data layer to be intermixed with duckdb, it seems to complicate the whole design
3. just write minimal code - to fetch data from a few rest api endpoints, collect it together and store to respective parquet files
4. management commands, if at all needed, should use a dry approach - ie pipeline logic should be clearly written elsewhere and this just calls that method 

5. For nav daily parquet updates,
Partition by month
nav/
  year=2026/
    month=08/
      part-0001.parquet
      part-0002.parquet
      part-0003.parquet

Every day:

Fetch today's NAVs.
Write one new Parquet file containing only today's rows.
Query all files together.

Example:

2026-08-01 -> part-0001.parquet
2026-08-02 -> part-0002.parquet
2026-08-03 -> part-0003.parquet

DuckDB happily reads:

SELECT *
FROM read_parquet('nav/year=2026/month=08/*.parquet');

No rewriting required.

6. When writing - follow the code convention for a clear ETL model, I want the extract written cleary as one method - which only does the fetch of the data (maybe called fetch_nav_daily or fetch_nav_history), then another method to store it into a parquet as (store_nav_daily), build_nav_daily - then calls fetch_nav+daily and store_nav_daily 

7. DONT MIX MANAGEMENT COMMANDS AND THIS TOGETHER. I DONT WANT TO SEE ARG PARSE UNNECESSARILY IN A DATA PIPELINE