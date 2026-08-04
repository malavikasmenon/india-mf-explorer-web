from datetime import date
from pathlib import Path

DATA_DIR = Path("data")


def schemes_path():
    return DATA_DIR / "schemes" / "schemes.parquet"


def nav_partition_path(nav_date: date):
    return (
        DATA_DIR
        / "nav"
        / f"year={nav_date:%Y}"
        / f"month={nav_date:%m}"
        / f"{nav_date:%Y-%m-%d}.parquet"
    )


def nav_month_path(year: int, month: int) -> Path:
    return (
        DATA_DIR
        / "nav"
        / f"year={year}"
        / f"month={month:02d}"
        / "history.parquet"
    )
