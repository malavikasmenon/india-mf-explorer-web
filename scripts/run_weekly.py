"""Refresh AUM and rebuild the manifest.

AMFI publishes scheme-wise average AUM once a quarter, not daily, on no
fixed date - running it on run_daily.py's schedule was mostly wasted
requests for a value that had not changed. Weekly is frequent enough to
pick up a newly published quarter within days, without polling an endpoint
on a schedule the underlying data can't keep up with.
"""

from data_pipeline.manifest import build_manifest
from data_pipeline.pipelines.aum import build_aum

build_aum()
build_manifest()
