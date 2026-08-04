"""One-time backfill: full NAV history for every scheme, then the manifest.

Run once against a fresh data store - after this, run_daily.py carries NAV
forward day by day. Safe to re-run, including after a crash or a cancelled
CI job: nav_backfill skips scheme codes it's already fetched and writes in
batches rather than all at once, so a resumed run picks up roughly where the
last one stopped instead of starting over. Schemes that still fail after a
retry are listed in data/nav_backfill_failures.json rather than failing the
whole run. There's no reason to run this on a schedule, though: history
doesn't change once it's been published.
"""

import pandas as pd

from data_pipeline.manifest import build_manifest
from data_pipeline.pipelines.nav_backfill import build_nav_backfill
from data_pipeline.pipelines.schemes import build_schemes
from data_pipeline.storage.paths import schemes_path

build_schemes()

scheme_codes = pd.read_parquet(schemes_path())["scheme_code"].tolist()
print(f"backfilling {len(scheme_codes)} schemes")

build_nav_backfill(scheme_codes)
build_manifest()
