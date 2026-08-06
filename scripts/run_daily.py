"""Fetch schemes, append today's NAV, compact closed months/years, and
rebuild the manifest.

Meant to run daily, after AMFI has published NAVAll.txt for the day (see
data_pipeline/clients/amfi.py). No arguments, no flags - the pipeline logic
lives in data_pipeline; this just calls it in order. Compaction runs before
the manifest rebuild so the manifest's file list matches what's actually on
disk afterward, not the pre-compaction layout.
"""

from data_pipeline.manifest import build_manifest
from data_pipeline.pipelines.nav_compaction import compact_nav, compact_nav_years
from data_pipeline.pipelines.nav_daily import build_nav_daily
from data_pipeline.pipelines.schemes import build_schemes

build_schemes()
build_nav_daily()
compact_nav()
compact_nav_years()
build_manifest()
