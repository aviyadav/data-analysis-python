"""Read every price and demand CSV in data/ and show the first five rows.

Every monthly file of the NSW1 dataset (PRICE_AND_DEMAND_<YYYYMM>_NSW1.csv,
2018-01 .. 2023-06) is read and concatenated into one time series before the
operations below run.

Usage:
    python main.py
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
CSV_GLOB = "PRICE_AND_DEMAND_*.csv"
DATE_FORMAT = "%Y/%m/%d %H:%M:%S"


def data_files(data_dir: Path = DATA_DIR) -> list[Path]:
    """Every price and demand CSV in data/, in file-name (monthly) order."""
    files = sorted(data_dir.glob(CSV_GLOB))
    if not files:
        raise FileNotFoundError(f"No files matching {CSV_GLOB} in {data_dir}")
    return files


def load_data(files: list[Path] | None = None) -> pd.DataFrame:
    """Read every monthly CSV into one frame ordered by SETTLEMENTDATE."""
    if files is None:
        files = data_files()

    frames = [
        pd.read_csv(
            path,
            parse_dates=["SETTLEMENTDATE"],
            date_format=DATE_FORMAT,
            engine="pyarrow",
        )
        for path in files
    ]

    combined = pd.concat(frames, ignore_index=True)
    return combined.sort_values("SETTLEMENTDATE").reset_index(drop=True)


def main() -> None:
    files = data_files()
    df = load_data(files)

    first, last = files[0].name, files[-1].name
    print(f"Files: {len(files)} CSVs in {DATA_DIR.name}/ ({first} .. {last})")
    print(f"Rows: {len(df)}  Columns: {list(df.columns)}\n")
    print("Top 5 rows:")
    print(df.head(5).to_string(index=False))

    df_copy = df.copy().assign(SETTLEMENTDATE=pd.to_datetime(df["SETTLEMENTDATE"], format=DATE_FORMAT))

    # Check the data type of the SETTLEMENTDATE column
    print(f"Data type of SETTLEMENTDATE column: {df_copy['SETTLEMENTDATE'].dtype}")

    # Extracting Date Components: Year, Month, Day
    df_copy = df_copy.assign(
        YEAR=df_copy["SETTLEMENTDATE"].dt.year,
        MONTH=df_copy["SETTLEMENTDATE"].dt.month,
        DAY=df_copy["SETTLEMENTDATE"].dt.day,
    )

    print("\nTop 5 rows with extracted date components:")
    print(df_copy.head(5).to_string(index=False))

    # Resampling Data by Time Intervals
    df_sample = df_copy.set_index("SETTLEMENTDATE").resample("1W").sum()['TOTALDEMAND']

    print("\nTop 5 rows of resampled data (weekly sum):")
    print(df_sample.head(5).to_string(index=True))

    # Difference Between Days with diff() and Timedelta()
    df_copy['MONTH_DIFFERENCE'] = df_copy['MONTH'].diff()

    print("\nTop 5 rows with month difference:")
    print(df_copy.head(5).to_string(index=False))

    # Calculate the time difference between consecutive rows in hours
    df_copy['TIME_DIFFERENCE_HOURS'] = df_copy['SETTLEMENTDATE'].diff() / pd.Timedelta(hours=1)
    
    # Convert the time difference from hours to minutes
    df_copy['TIME_DIFFERENCE_MINUTES'] = df_copy['SETTLEMENTDATE'].diff() / pd.Timedelta(minutes=1)

    print("\nTop 5 rows with hour and minute difference:")
    print(df_copy.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
