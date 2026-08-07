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


def nav_year_path(year: int) -> Path:
    return DATA_DIR / "nav" / f"year={year}" / "history.parquet"


def aum_partition_path(period_start: date) -> Path:
    # One file per quarter, named for the quarter's first month - AUM has no
    # daily grain to compact the way nav does, so there is nothing finer to
    # partition by.
    return (
        DATA_DIR
        / "aum"
        / f"year={period_start:%Y}"
        / f"{period_start:%Y-%m}.parquet"
    )


def ter_partition_path(ter_date: date) -> Path:
    return (
        DATA_DIR
        / "ter"
        / f"year={ter_date:%Y}"
        / f"month={ter_date:%m}"
        / f"{ter_date:%Y-%m-%d}.parquet"
    )


def ter_month_path(year: int, month: int) -> Path:
    return (
        DATA_DIR
        / "ter"
        / f"year={year}"
        / f"month={month:02d}"
        / "history.parquet"
    )


def ter_year_path(year: int) -> Path:
    return DATA_DIR / "ter" / f"year={year}" / "history.parquet"
