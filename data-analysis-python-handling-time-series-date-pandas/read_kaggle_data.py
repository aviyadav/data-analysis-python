"""Download the NSW1 price and demand dataset from Kaggle and read all of it.

The Kaggle dataset "joebeachcapital/nsw-australia-electricity-demand-2018-2023"
is a mirror of AEMO's aggregated price and demand files: one CSV per month,
named PRICE_AND_DEMAND_<YYYYMM>_NSW1.csv, covering 2018-01 through 2023-06.

On first run the monthly files are downloaded from Kaggle's public download
endpoint (this works without credentials because the dataset is public) and
extracted into data/. Afterwards the whole 2018-01..2023-06 range is read into
one time series and summarised.

The official alternatives are the Kaggle CLI (`kaggle datasets download -d
<slug>`) or `kagglehub.dataset_download(<slug>)`; both need an API token from
https://www.kaggle.com/settings/account.

Usage:
    python read_kaggle_data.py [--force-download] [--rows N]
"""

from __future__ import annotations

import argparse
import io
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

DATASET_SLUG = "joebeachcapital/nsw-australia-electricity-demand-2018-2023"
DOWNLOAD_URL = f"https://www.kaggle.com/api/v1/datasets/download/{DATASET_SLUG}"

DATA_DIR = Path(__file__).resolve().parent / "data"
REGION = "NSW1"
FIRST_MONTH = (2018, 1)
LAST_MONTH = (2023, 6)
DATE_FORMAT = "%Y/%m/%d %H:%M:%S"
DOWNLOAD_TIMEOUT_SECONDS = 180


def month_range(first: tuple[int, int], last: tuple[int, int]) -> list[str]:
    """Every YYYYMM string from first to last, inclusive."""
    months: list[str] = []
    year, month = first
    while (year, month) <= last:
        months.append(f"{year:04d}{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def month_file(month: str) -> Path:
    """Path of the monthly CSV for a YYYYMM string."""
    return DATA_DIR / f"PRICE_AND_DEMAND_{month}_{REGION}.csv"


def expected_files() -> list[Path]:
    """The 66 monthly files that make up the dataset."""
    return [month_file(month) for month in month_range(FIRST_MONTH, LAST_MONTH)]


def missing_files() -> list[Path]:
    """Expected files that are not on disk yet."""
    return [path for path in expected_files() if not path.is_file()]


def download_dataset() -> int:
    """Download the dataset zip and extract the monthly CSVs into data/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {DOWNLOAD_URL}")

    request = urllib.request.Request(
        DOWNLOAD_URL, headers={"User-Agent": "python-urllib/kaggle-dataset-reader"}
    )
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        payload = response.read()

    print(f"Received {len(payload) / 1024:.1f} KiB, extracting ...")

    written = 0
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        wanted = {path.name for path in expected_files()}
        for member in archive.namelist():
            name = Path(member).name  # the archive stores the CSVs at its root
            if name in wanted:
                (DATA_DIR / name).write_bytes(archive.read(member))
                written += 1

    return written


def ensure_dataset(force_download: bool = False) -> None:
    """Make sure every monthly file of the dataset is available in data/."""
    expected = expected_files()
    missing = missing_files()

    if force_download or missing:
        if missing and not force_download:
            print(f"{len(missing)} of {len(expected)} monthly files are missing.")
        written = download_dataset()
        print(f"Extracted {written} monthly files into {DATA_DIR}")
    else:
        print(f"All {len(expected)} monthly files are already present in {DATA_DIR}")

    still_missing = missing_files()
    if still_missing:
        names = ", ".join(path.name for path in still_missing)
        raise FileNotFoundError(f"dataset is incomplete, missing: {names}")


def load_dataset() -> pd.DataFrame:
    """Read every monthly CSV into one frame ordered by SETTLEMENTDATE."""
    frames = [
        pd.read_csv(
            path,
            parse_dates=["SETTLEMENTDATE"],
            date_format=DATE_FORMAT,
            engine="pyarrow",
        )
        for path in expected_files()
    ]

    combined = pd.concat(frames, ignore_index=True)
    return combined.sort_values("SETTLEMENTDATE").reset_index(drop=True)


def print_summary(frame: pd.DataFrame, rows: int) -> None:
    """Report what was read: shape, range, step sizes and first/last rows."""
    months = month_range(FIRST_MONTH, LAST_MONTH)
    timestamps = frame["SETTLEMENTDATE"]
    steps = timestamps.diff().dropna().value_counts().sort_index()

    print(f"\nDataset:  {DATASET_SLUG}")
    print(f"Files:    {len(months)} monthly CSVs, {months[0]} .. {months[-1]}")
    print(f"Rows:     {len(frame)}")
    print(f"Columns:  {list(frame.columns)}")
    print(f"Range:    {timestamps.min()} .. {timestamps.max()}")
    print(f"Regions:  {frame['REGION'].unique().tolist()}")
    print(f"Duplicate timestamps: {int(timestamps.duplicated().sum())}")

    print("\nObserved step between consecutive rows:")
    for step, count in steps.items():
        print(f"  {step} -> {count} rows")

    print("\nRows per year:")
    for year, count in timestamps.dt.year.value_counts().sort_index().items():
        print(f"  {year}: {count}")

    print("\nData types:")
    for column, dtype in frame.dtypes.items():
        print(f"  {column}: {dtype}")

    print(f"\nFirst {rows} rows:")
    print(frame.head(rows).to_string(index=False))
    print(f"\nLast {rows} rows:")
    print(frame.tail(rows).to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="download the dataset again even when the monthly files already exist",
    )
    parser.add_argument(
        "--rows", type=int, default=5, help="rows to display at each end (default 5)"
    )
    args = parser.parse_args()

    ensure_dataset(force_download=args.force_download)
    frame = load_dataset()
    print_summary(frame, args.rows)


if __name__ == "__main__":
    main()
