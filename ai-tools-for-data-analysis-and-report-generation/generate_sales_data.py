import json
import sqlite3
from calendar import monthrange
from pathlib import Path

import numpy as np
import polars as pl

OUT = Path.cwd() / "data"
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(42)
customers = pl.DataFrame(
    {
        "customer_id": [f"C{i:04d}" for i in range(1, 401)],
        "customer_segment": rng.choice(
            ["Consumer", "Corporate", "Small Business"], 400, p=[0.55, 0.25, 0.20]
        ),
    }
)
frames = []
for month, count in enumerate([220, 260, 310, 280, 390, 540], start=1):
    start = np.datetime64(f"2026-{month:02d}-01")
    dates = start + rng.integers(0, monthrange(2026, month)[1], count).astype(
        "timedelta64[D]"
    )
    customer = customers[rng.integers(0, len(customers), count)]
    category = rng.choice(
        ["Electronics", "Home", "Office"], count, p=[0.30, 0.40, 0.30]
    )
    base = (
        pl.Series(category)
        .replace_strict({"Electronics": 180, "Home": 65, "Office": 25})
        .to_numpy()
    )
    quantity = rng.integers(1, 5, count) + np.where(
        customer["customer_segment"].to_numpy() == "Corporate", 2, 0
    )
    price = np.round(base * rng.uniform(0.8, 1.2, count), 2)
    discount = rng.choice(
        [0.0, 0.05, 0.10, 0.20],
        count,
        p=[0.15, 0.20, 0.25, 0.40] if month == 4 else [0.50, 0.25, 0.20, 0.05],
    )
    frames.append(
        customer.with_columns(
            order_date=dates,
            product_category=category,
            quantity=quantity,
            unit_price=price,
            discount=discount,
            net_revenue=np.round(quantity * price * (1 - discount), 2),
        )
    )
sales = pl.concat(frames).sort("order_date", maintain_order=True)
sales.insert_column(
    0, pl.Series("order_id", [f"O{i:05d}" for i in range(1, len(sales) + 1)])
)
sales = sales.select(
    "order_id",
    "order_date",
    "customer_id",
    "customer_segment",
    "product_category",
    "quantity",
    "unit_price",
    "discount",
    "net_revenue",
)
sales.write_csv(OUT / "sales_data.csv", date_format="%Y-%m-%d")
# Calculate from the saved file, just as the applications will.
df = pl.read_csv(OUT / "sales_data.csv", try_parse_dates=True)
df = df.with_columns(month=pl.col("order_date").dt.strftime("%Y-%m"))


def summary(keys):
    return (
        df.group_by(keys)
        .agg(revenue=pl.col("net_revenue").sum(), orders=pl.col("order_id").n_unique())
        .sort(keys)
        .with_columns(average_order_value=pl.col("revenue") / pl.col("orders"))
    )


monthly = summary("month").with_columns(
    revenue_change_pct=pl.col("revenue").pct_change() * 100
)
segments = summary("customer_segment")
monthly.write_csv(OUT / "reference_monthly.csv", float_precision=6)
segments.write_csv(OUT / "reference_segments.csv", float_precision=6)
metrics = {
    "orders": df["order_id"].n_unique(),
    "revenue": round(df["net_revenue"].sum(), 2),
    "average_order_value": round(
        df["net_revenue"].sum() / df["order_id"].n_unique(), 6
    ),
}
(OUT / "reference_metrics.json").write_text(
    json.dumps(metrics, indent=2), encoding="utf-8"
)
with sqlite3.connect(OUT / "sales.db") as connection:
    connection.execute("DROP TABLE IF EXISTS sales")
    connection.execute("""CREATE TABLE sales (
        order_id TEXT, order_date TIMESTAMP, customer_id TEXT, customer_segment TEXT,
        product_category TEXT, quantity INTEGER, unit_price REAL, discount REAL, net_revenue REAL
    )""")
    connection.executemany(
        "INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        df.drop("month")
        .with_columns(pl.col("order_date").dt.strftime("%Y-%m-%d 00:00:00"))
        .iter_rows(),
    )
assert len(df) == 2000 and df["order_id"].n_unique() == len(df)
assert np.allclose(
    df["net_revenue"],
    np.round(
        df["quantity"].to_numpy()
        * df["unit_price"].to_numpy()
        * (1 - df["discount"].to_numpy()),
        2,
    ),
)
assert (
    df.group_by("customer_id")
    .agg(pl.col("customer_segment").n_unique())["customer_segment"]
    .max()
    == 1
)
print(json.dumps(metrics, indent=2))
with pl.Config(tbl_formatting="ASCII_FULL"):
    print(monthly.with_columns(pl.col(pl.Float64).round(2)))
    print(segments.with_columns(pl.col(pl.Float64).round(2)))
