from data_pipeline.manifest import build_manifest
from data_pipeline.pipelines.schemes import build_schemes
from data_pipeline.pipelines.nav_daily import build_nav_daily
from data_pipeline.pipelines.nav_backfill import build_nav_backfill

# build_schemes()

# build_nav_daily()

#build_nav_backfill(scheme_codes)

import pandas as pd

df = pd.read_parquet("data/schemes/schemes.parquet")
scheme_codes = df["scheme_code"].tolist()
print(f"Fetched {len(scheme_codes)} scheme codes")
build_nav_backfill(scheme_codes)

# build_manifest()