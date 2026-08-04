"""Fetch schemes, append today's NAV, and rebuild the manifest.

Meant to run daily, after AMFI has published NAVAll.txt for the day (see
data_pipeline/clients/amfi.py). No arguments, no flags - the pipeline logic
lives in data_pipeline; this just calls it in order.
"""

from data_pipeline.manifest import build_manifest
from data_pipeline.pipelines.nav_daily import build_nav_daily
from data_pipeline.pipelines.schemes import build_schemes

build_schemes()
build_nav_daily()
build_manifest()
