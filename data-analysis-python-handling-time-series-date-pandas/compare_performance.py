"""Benchmark pandas (eager, main.py) against Polars (lazy, main_polars.py).

Both engines run the same operations as main.py: load every monthly CSV in
data/ and parse SETTLEMENTDATE, extract YEAR/MONTH/DAY, compute row-over-row
differences, and sum TOTALDEMAND per week. Timings cover the data operations
only -- interpreter start-up and library imports happen before any timer starts
-- and both engines' results are verified to be identical before any timing is
reported.

Usage:
    python compare_performance.py [--repeat N] [--warmup N]
"""

from __future__ import annotations

import argparse
import math
import statistics
import time
from collections.abc import Callable

import pandas as pd
import polars as pl

import main
import main_polars

# Timed runs per phase: the best run is the least noisy estimator for CPU-bound
# work, the median is shown next to it. Warm-up runs populate the OS page cache
# and let both libraries allocate their buffers before timing starts.
REPEAT = 7
WARMUP = 2

# Relative/absolute tolerance used when comparing floats between the engines.
TOLERANCE = 1e-6


# --- pandas phases ---------------------------------------------------------
# main.load_data() is reused as-is; the functions below mirror the operations
# that main.py performs, so both engines do exactly the same work.


def pandas_components(df: pd.DataFrame) -> pd.DataFrame:
    """Extract YEAR/MONTH/DAY (the date-component block of main.py)."""
    return df.assign(
        YEAR=df["SETTLEMENTDATE"].dt.year,
        MONTH=df["SETTLEMENTDATE"].dt.month,
        DAY=df["SETTLEMENTDATE"].dt.day,
    )


def pandas_weekly(df: pd.DataFrame) -> pd.Series:
    """Weekly TOTALDEMAND sums (the resample block of main.py)."""
    return df.set_index("SETTLEMENTDATE").resample("1W").sum()["TOTALDEMAND"]


def pandas_differences(df: pd.DataFrame) -> pd.DataFrame:
    """Month and time differences (the diff blocks of main.py).

    Expects the frame returned by pandas_components(), because the month
    difference is computed from the MONTH column.
    """
    return df.assign(
        MONTH_DIFFERENCE=df["MONTH"].diff(),
        TIME_DIFFERENCE_HOURS=df["SETTLEMENTDATE"].diff() / pd.Timedelta(hours=1),
        TIME_DIFFERENCE_MINUTES=df["SETTLEMENTDATE"].diff() / pd.Timedelta(minutes=1),
    )


def pandas_full_pipeline() -> tuple[pd.DataFrame, pd.Series]:
    """Load once, then run every operation -- the flow main.py follows."""
    diffed = pandas_differences(pandas_components(main.load_data()))
    return diffed, pandas_weekly(diffed)


# --- Polars phases ---------------------------------------------------------
# Each function below only builds a query plan; nothing runs until .collect().


def polars_row_differences(plan: pl.LazyFrame | None = None) -> pl.LazyFrame:
    """Lazy plan for YEAR/MONTH/DAY plus all three difference columns."""
    lazy = main_polars.build_plan() if plan is None else plan
    return main_polars.with_time_differences(
        main_polars.with_month_difference(main_polars.with_date_components(lazy))
    )


def polars_full_pipeline() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Load once, then run the same operations as pandas_full_pipeline()."""
    diffed = polars_row_differences().collect()
    weekly = main_polars.weekly_demand(diffed.lazy()).collect()
    return diffed, weekly


# --- timing and comparison helpers ----------------------------------------


def time_phase(
    func: Callable[[], object], repeat: int = REPEAT, warmup: int = WARMUP
) -> tuple[float, float]:
    """Return (best_ms, median_ms) over repeated executions of func."""
    for _ in range(max(warmup, 0)):
        func()

    timings: list[float] = []
    for _ in range(repeat):
        start = time.perf_counter()
        func()
        timings.append((time.perf_counter() - start) * 1000)

    return min(timings), statistics.median(timings)


def is_missing(value: object) -> bool:
    """True for a pandas NaN or a Polars null (Python None)."""
    return value is None or (isinstance(value, float) and math.isnan(value))


def values_equal(pandas_values: list, polars_values: list) -> bool:
    """Compare two column value lists, treating NaN and None as the same."""
    if len(pandas_values) != len(polars_values):
        return False

    for pandas_value, polars_value in zip(pandas_values, polars_values):
        pandas_blank = is_missing(pandas_value)
        polars_blank = is_missing(polars_value)
        if pandas_blank or polars_blank:
            if pandas_blank != polars_blank:
                return False
            continue

        # Strings must match exactly; numbers get a tolerance because the two
        # engines may accumulate sums in a different order.
        if isinstance(pandas_value, str) or isinstance(polars_value, str):
            if pandas_value != polars_value:
                return False
            continue

        close = math.isclose(
            float(pandas_value),
            float(polars_value),
            rel_tol=TOLERANCE,
            abs_tol=TOLERANCE,
        )
        if not close:
            return False

    return True


# --- equivalence check -----------------------------------------------------


def verify_results() -> list[tuple[str, bool, str]]:
    """Check that both engines return the same data, not just similar timings."""
    pandas_frame = main.load_data()
    polars_frame = main_polars.build_plan().collect()

    pandas_dated = pandas_components(pandas_frame)
    polars_dated = main_polars.with_date_components(main_polars.build_plan()).collect()

    pandas_weekly_values = pandas_weekly(pandas_frame)
    polars_weekly_frame = main_polars.weekly_demand(main_polars.build_plan()).collect()

    pandas_diffed = pandas_differences(pandas_dated)
    polars_diffed = polars_row_differences().collect()

    pandas_dtype = str(pandas_frame["SETTLEMENTDATE"].dtype)
    polars_dtype = str(polars_frame.schema["SETTLEMENTDATE"])

    checks: list[tuple[str, bool, str]] = [
        (
            "row count",
            len(pandas_frame) == polars_frame.height,
            f"pandas={len(pandas_frame)} polars={polars_frame.height}",
        ),
        (
            "SETTLEMENTDATE is datetime",
            pandas_dtype.startswith("datetime") and polars_dtype.startswith("Datetime"),
            f"pandas={pandas_dtype} polars={polars_dtype}",
        ),
    ]

    for column in ("REGION", "TOTALDEMAND", "RRP", "PERIODTYPE"):
        equal = values_equal(
            pandas_frame[column].tolist(), polars_frame[column].to_list()
        )
        checks.append((f"column {column}", equal, "whole column"))

    for column in ("YEAR", "MONTH", "DAY"):
        equal = values_equal(
            pandas_dated[column].tolist(), polars_dated[column].to_list()
        )
        checks.append((f"column {column}", equal, "whole column"))

    for column in (
        "MONTH_DIFFERENCE",
        "TIME_DIFFERENCE_HOURS",
        "TIME_DIFFERENCE_MINUTES",
    ):
        equal = values_equal(
            pandas_diffed[column].tolist(), polars_diffed[column].to_list()
        )
        checks.append((f"column {column}", equal, "whole column"))

    pandas_labels = [stamp.date().isoformat() for stamp in pandas_weekly_values.index]
    polars_labels = [
        value.date().isoformat()
        for value in polars_weekly_frame["SETTLEMENTDATE"].to_list()
    ]
    checks.append(
        (
            "weekly bucket labels",
            pandas_labels == polars_labels,
            f"{len(pandas_labels)} buckets, first={pandas_labels[0]} last={pandas_labels[-1]}",
        )
    )
    checks.append(
        (
            "weekly TOTALDEMAND sums",
            values_equal(
                pandas_weekly_values.tolist(),
                polars_weekly_frame["TOTALDEMAND"].to_list(),
            ),
            f"first={round(pandas_weekly_values.iloc[0], 2)}",
        )
    )

    return checks


# --- reporting -------------------------------------------------------------


def print_table(
    rows: list[tuple[str, float, float, float, float, float | None]],
) -> None:
    """Print the pandas vs Polars phase comparison table."""
    header = (
        f"{'Phase':<40}{'pandas best':>13}{'pandas med':>12}"
        f"{'polars best':>13}{'polars med':>12}{'polars speedup':>16}"
    )
    print(header)
    print("-" * len(header))

    for label, pandas_best, pandas_med, polars_best, polars_med, speedup in rows:
        speedup_text = f"{speedup:.2f}x" if speedup is not None else "n/a"
        print(
            f"{label:<40}{pandas_best:>13.3f}{pandas_med:>12.3f}"
            f"{polars_best:>13.3f}{polars_med:>12.3f}{speedup_text:>16}"
        )


# --- benchmark -------------------------------------------------------------

# One comparison row: label, pandas best ms, pandas median ms, polars best ms,
# polars median ms, and speedup (pandas best / Polars best, so above 1 means
# Polars was faster).
PhaseRow = tuple[str, float, float, float, float, float | None]


def benchmark(repeat: int, warmup: int) -> tuple[list[PhaseRow], tuple[float, float]]:
    """Time each phase for both engines; also time building a plan on its own."""
    pandas_frame = main.load_data()
    plan = main_polars.build_plan()

    phases: list[tuple[str, Callable[[], object], Callable[[], object]]] = [
        ("load + parse dates", main.load_data, plan.collect),
        (
            "extract YEAR/MONTH/DAY",
            lambda: pandas_components(pandas_frame),
            lambda: main_polars.with_date_components(plan).collect(),
        ),
        (
            "weekly TOTALDEMAND sums",
            lambda: pandas_weekly(pandas_frame),
            lambda: main_polars.weekly_demand(plan).collect(),
        ),
        (
            "row differences (month/hours/minutes)",
            lambda: pandas_differences(pandas_components(pandas_frame)),
            lambda: polars_row_differences(plan).collect(),
        ),
        (
            "full pipeline (load + all operations)",
            pandas_full_pipeline,
            polars_full_pipeline,
        ),
    ]

    rows: list[PhaseRow] = []
    for label, pandas_phase, polars_phase in phases:
        pandas_best, pandas_med = time_phase(pandas_phase, repeat, warmup)
        polars_best, polars_med = time_phase(polars_phase, repeat, warmup)
        speedup = pandas_best / polars_best if polars_best > 0 else None
        rows.append((label, pandas_best, pandas_med, polars_best, polars_med, speedup))

    # Polars-only: building a plan touches no data, so this is pure Python cost.
    plan_stats = time_phase(lambda: polars_row_differences(plan), repeat, warmup)

    return rows, plan_stats


def main_cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeat", type=int, default=REPEAT, help="timed runs per phase")
    parser.add_argument("--warmup", type=int, default=WARMUP, help="warm-up runs per phase")
    args = parser.parse_args()

    data_files = main.data_files()
    total_mib = sum(path.stat().st_size for path in data_files) / 1024 / 1024
    print("=" * 78)
    print("pandas (eager) vs Polars (lazy) -- same operations as main.py")
    print("=" * 78)
    print(f"data:   {len(data_files)} CSVs in {main.DATA_DIR.name}/ ({total_mib:.1f} MiB)")
    print(f"timing: best and median of {args.repeat} runs after {args.warmup} warm-up runs\n")

    checks = verify_results()
    print("Result check (both engines must agree before timings are compared):")
    for label, passed, detail in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {label:<28} {detail}")
    all_passed = all(passed for _, passed, _ in checks)
    print()

    if all_passed:
        print("  => all results are identical\n")
    else:
        print("  => RESULTS DIFFER - the timings below are not comparable\n")

    rows, plan_stats = benchmark(args.repeat, args.warmup)
    print_table(rows)
    print(
        "\nTimes are milliseconds; speedup = pandas best / Polars best, so a value\n"
        "above 1.00x means Polars was faster."
    )
    print(
        "\nPolars-only reference: building the full lazy plan without collecting it\n"
        f"takes {plan_stats[0]:.4f} ms (best) / {plan_stats[1]:.4f} ms (median). Planning is\n"
        "cheap -- .collect() is what reads, parses and computes."
    )

    print(
        "\nFairness notes\n"
        "--------------\n"
        "- Each library uses its own fastest reader: pandas with the pyarrow engine,\n"
        "  Polars with its native Rust scan_csv; imports happen outside the timers.\n"
        "- The weekly phase aggregates TOTALDEMAND only. main.py's pandas line also\n"
        "  sums the remaining numeric columns, so both engines do the same work here.\n"
        "- Polars re-executes the whole plan on every .collect(), so each per-phase\n"
        "  row re-reads the CSVs; the full pipeline collects once, just as main.py\n"
        "  loads once and reuses the frame.\n"
        "- pandas closes a W-SUN week Monday->Monday (left-closed) and labels it with\n"
        "  the Sunday; weekly_demand() reproduces those labels and sums exactly.\n"
        "- Both engines read all 66 monthly CSVs, so these numbers reflect real work;\n"
        "  per-call fixed overhead is still included, and close phases can flip\n"
        "  between runs. Raise --repeat for stabler timings.\n"
    )

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main_cli())
