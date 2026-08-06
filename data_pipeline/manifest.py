"""Build manifest.json - the index the browser reads to discover the dataset.

The frontend contains no table names, column names or file paths; it fetches this
file and builds itself from it. So a new table reaches the UI by being written to
`data/`, not by anyone editing JavaScript. That is the whole contract.

The manifest also enumerates each table's Parquet files explicitly, because
`read_parquet` cannot glob over plain HTTPS - a public bucket exposes no listing
to glob against.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from data_pipeline.dictionary import COLUMNS, NOT_NULL, PRIMARY_KEY, TABLES

MANIFEST_NAME = "manifest.json"
DATA_DIR = Path("data")


def discover(data_dir: Path) -> dict[str, list[Path]]:
    """Map table name -> its Parquet files, sorted.

    Two layouts, because `nav` is partitioned by month and `schemes` never
    will be: a bare `schemes.parquet` is the single file of table `schemes`;
    every `*.parquet` under a `nav/` directory is a partition of table `nav`.
    """
    tables: dict[str, list[Path]] = {}

    for path in sorted(data_dir.glob("*.parquet")):
        tables.setdefault(path.stem, []).append(path)

    for child in sorted(data_dir.iterdir()):
        if not child.is_dir():
            continue
        # Newest first, not oldest first. DuckDB's TopN pushdown for
        # `ORDER BY <partition col> DESC LIMIT n` narrows its threshold
        # adaptively as it scans files in the order it's given them, rather
        # than consulting every file's footer stats upfront - given the
        # files oldest-first, it doesn't find a tight threshold until it's
        # already scanned nearly everything. Newest-first, it tightens
        # immediately and skips the rest. Measured: ~41s -> ~18s on the
        # `nav` table's 245 files for `ORDER BY date DESC LIMIT 10`.
        partitions = sorted(child.rglob("*.parquet"), reverse=True)
        if partitions:
            tables.setdefault(child.name, []).extend(partitions)

    return tables


def describe(con: duckdb.DuckDBPyConnection, name: str, files: list[Path]) -> dict:
    """Measure one table from the Parquet itself, then layer the prose on top."""
    paths = [str(p) for p in files]

    # A list literal even for one file, so the single-file and partitioned cases
    # take the identical path here and in the browser. hive_partitioning=false
    # because the year=/month= folders are a storage layout, not columns - left
    # on, DuckDB auto-detects them and synthesizes redundant year/month columns
    # that duplicate what `date` already carries.
    source = f"read_parquet({paths!r}, hive_partitioning = false)"

    schema = con.execute(f"DESCRIBE SELECT * FROM {source}").fetchall()
    (row_count,) = con.execute(f"SELECT count(*) FROM {source}").fetchone()

    prose = TABLES.get(name, {})
    column_prose = COLUMNS.get(name, {})
    not_null = NOT_NULL.get(name, set())
    key = PRIMARY_KEY.get(name, [])

    return {
        "name": name,
        "title": prose.get("title", name),
        "subtitle": prose.get("subtitle"),
        "grain": prose.get("grain"),
        "description": prose.get("description"),
        "examples": prose.get("examples", []),
        "primary_key": key,
        "row_count": row_count,
        "columns": [
            {
                "name": column,
                "type": dtype,
                # Not from DESCRIBE: Parquet carries no NOT NULL, so every column
                # reads back as nullable regardless of what the pipeline proved.
                "nullable": column not in not_null,
                "primary_key": column in key,
                **column_prose.get(column, {}),
            }
            for column, dtype, *_ in schema
        ],
    }


def build_catalog(data_dir: Path) -> dict:
    con = duckdb.connect()
    tables = []

    for name, files in sorted(discover(data_dir).items()):
        entry = describe(con, name, files)
        entry["files"] = [str(p.relative_to(data_dir)) for p in files]
        entry["bytes"] = sum(p.stat().st_size for p in files)

        # Provenance is written per build by the table's own builder; the manifest
        # republishes it rather than restating it, so there is one source of truth.
        sidecar = data_dir / f"{name}.ingest.json"
        if sidecar.exists():
            entry["source"] = json.loads(sidecar.read_text()).get("source")

        tables.append(entry)

    con.close()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tables": tables,
    }


def store_manifest(manifest: dict, data_dir: Path) -> None:
    (data_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n")


def build_manifest(data_dir: Path = DATA_DIR) -> dict:
    manifest = build_catalog(data_dir)
    store_manifest(manifest, data_dir)
    return manifest
