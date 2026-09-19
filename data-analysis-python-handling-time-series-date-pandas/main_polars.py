"""Same operations as main.py, implemented with Polars lazy loading.

Every monthly CSV in data/ (PRICE_AND_DEMAND_<YYYYMM>_NSW1.csv, 2018-01 ..
2023-06) is scanned as a single lazy query.

A Polars LazyFrame only records a query *plan*: no CSV data is read, parsed or
computed until .collect() is called. Because of that, every .collect() below
executes the whole plan again -- a LazyFrame is a query description, not cached
data. Collect once (or reuse an already collected frame via .lazy()) when you
want to avoid re-reading the CSVs for each section.

Usage:
    python main_polars.py
"""

from pathlib import Path

import polars as pl

DATA_DIR = Path(__file__).resolve().parent / "data"
CSV_GLOB = "PRICE_AND_DEMAND_*.csv"
DATE_FORMAT = "%Y/%m/%d %H:%M:%S"


def data_files(data_dir: Path = DATA_DIR) -> list[Path]:
    """Every price and demand CSV in data/, in file-name (monthly) order."""
    files = sorted(data_dir.glob(CSV_GLOB))
    if not files:
        raise FileNotFoundError(f"No files matching {CSV_GLOB} in {data_dir}")
    return files


def build_plan(files: list[Path] | None = None) -> pl.LazyFrame:
    """Build the lazy plan over all monthly CSVs; nothing is read until collect()."""
    if files is None:
        files = data_files()

    return (
        pl.scan_csv([str(path) for path in files])
        .with_columns(pl.col("SETTLEMENTDATE").str.to_datetime(DATE_FORMAT, strict=True))
        .sort("SETTLEMENTDATE")
    )


def with_date_components(lazy: pl.LazyFrame) -> pl.LazyFrame:
    """Extract YEAR, MONTH and DAY from SETTLEMENTDATE (lazily)."""
    return lazy.with_columns(
        pl.col("SETTLEMENTDATE").dt.year().alias("YEAR"),
        pl.col("SETTLEMENTDATE").dt.month().alias("MONTH"),
        pl.col("SETTLEMENTDATE").dt.day().alias("DAY"),
    )


def weekly_demand(lazy: pl.LazyFrame) -> pl.LazyFrame:
    """Weekly TOTALDEMAND sums, matching pandas resample("1W") (W-SUN buckets).

    pandas splits a W-SUN week as a left-closed Monday->Monday window labelled
    with the Sunday that ends it, while Polars labels a window with its start
    edge. Building Monday-start, left-closed windows and shifting the label by
    6 days therefore reproduces the pandas buckets exactly.
    """
    return (
        lazy.group_by_dynamic(
            "SETTLEMENTDATE",
            every="1w",
            closed="left",
            label="left",
            start_by="monday",
        )
        .agg(pl.col("TOTALDEMAND").sum())
        .with_columns(pl.col("SETTLEMENTDATE").dt.offset_by("6d"))
        .sort("SETTLEMENTDATE")
    )


def with_month_difference(lazy: pl.LazyFrame) -> pl.LazyFrame:
    """Row-over-row difference of MONTH (float, like pandas .diff())."""
    return lazy.with_columns(
        pl.col("MONTH").diff().cast(pl.Float64).alias("MONTH_DIFFERENCE"),
    )


def with_time_differences(lazy: pl.LazyFrame) -> pl.LazyFrame:
    """Row-over-row time difference expressed in hours and in minutes."""
    return lazy.with_columns(
        (pl.col("SETTLEMENTDATE").diff().dt.total_seconds() / 3600).alias(
            "TIME_DIFFERENCE_HOURS"
        ),
        (pl.col("SETTLEMENTDATE").diff().dt.total_seconds() / 60).alias(
            "TIME_DIFFERENCE_MINUTES"
        ),
    )


def main() -> None:
    files = data_files()
    plan = build_plan(files)

    first, last = files[0].name, files[-1].name
    print(f"Files: {len(files)} CSVs in {DATA_DIR.name}/ ({first} .. {last})")

    # 1. Top 5 rows -- the first .collect() is what actually reads and parses.
    df = plan.collect()
    print(f"Rows: {df.height}  Columns: {df.columns}\n")
    print("Top 5 rows:")
    print(df.head(5))

    # Check the data type of the SETTLEMENTDATE column
    print(f"Data type of SETTLEMENTDATE column: {df.schema['SETTLEMENTDATE']}")

    # Extracting Date Components: Year, Month, Day
    dated = with_date_components(plan)
    print("\nTop 5 rows with extracted date components:")
    print(dated.collect().head(5))

    # Resampling Data by Time Intervals
    print("\nTop 5 rows of resampled data (weekly sum):")
    print(weekly_demand(plan).collect().head(5))

    # Difference Between Days with diff() and Timedelta()
    month_diff = with_month_difference(dated)
    print("\nTop 5 rows with month difference:")
    print(month_diff.collect().head(5))

    # Calculate the time difference between consecutive rows in hours, then minutes
    all_diffs = with_time_differences(month_diff)
    print("\nTop 5 rows with hour and minute difference:")
    print(all_diffs.collect().head(5))


if __name__ == "__main__":
    main()
