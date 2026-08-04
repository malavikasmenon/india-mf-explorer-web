# storage/metadata.py

import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path("data")


def write_ingest_metadata(dataset: str, source: dict):
    path = DATA_DIR / f"{dataset}.ingest.json"

    path.write_text(
        json.dumps(
            {
                "source": source,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
    )