"""Fetch schemes, append today's NAV, refresh TER, compact closed
months/years, and rebuild the manifest.

Meant to run daily, after AMFI has published NAVAll.txt for the day (see
data_pipeline/clients/amfi.py). No arguments, no flags - the pipeline logic
lives in data_pipeline; this just calls it in order. Compaction runs before
the manifest rebuild so the manifest's file list matches what's actually on
disk afterward, not the pre-compaction layout.

AUM is not refreshed here - AMFI publishes it once a quarter, not daily, so
it runs on its own schedule (see run_weekly.py) instead of on this one.
"""

from data_pipeline.manifest import build_manifest
from data_pipeline.pipelines.nav_compaction import compact_nav, compact_nav_years
from data_pipeline.pipelines.nav_daily import build_nav_daily
from data_pipeline.pipelines.schemes import build_schemes
from data_pipeline.pipelines.ter import build_ter
from data_pipeline.pipelines.ter_compaction import compact_ter, compact_ter_years

build_schemes()
build_nav_daily()
build_ter()
compact_nav()
compact_nav_years()
compact_ter()
compact_ter_years()
build_manifest()
