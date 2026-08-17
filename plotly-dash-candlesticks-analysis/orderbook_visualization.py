import argparse
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


SNAPSHOT_PATTERN = "*-snapshots-*.txt"


def find_latest_snapshot_file() -> Path:
    snapshot_files = sorted(Path(".").glob(SNAPSHOT_PATTERN), key=lambda path: path.stat().st_mtime)
    if not snapshot_files:
        raise FileNotFoundError(
            f"No order book snapshot files found matching {SNAPSHOT_PATTERN!r}. "
            "Run orderbook.py first, or pass --file with a snapshot file path."
        )
    return snapshot_files[-1]


def load_snapshot(path: Path, snapshot_index: int = -1) -> dict:
    with path.open(encoding="utf-8") as file:
        snapshots = [json.loads(line) for line in file if line.strip()]

    if not snapshots:
        raise ValueError(f"No snapshots found in {path}")

    try:
        return snapshots[snapshot_index]
    except IndexError as exc:
        raise IndexError(
            f"Snapshot index {snapshot_index} is out of range for {path}; "
            f"file contains {len(snapshots)} snapshots."
        ) from exc


def build_orderbook_side(snapshot: dict, side: str, levels: int) -> pd.DataFrame:
    rows = snapshot.get(side, [])[:levels]
    if not rows:
        return pd.DataFrame(columns=["price", "quantity", "notional", "cumulative_quantity"])

    data = pd.DataFrame(rows, columns=["price", "quantity"])
    data[["price", "quantity"]] = data[["price", "quantity"]].astype(float)
    data["notional"] = data["price"] * data["quantity"]

    if side == "bids":
        data = data.sort_values("price", ascending=False)
    else:
        data = data.sort_values("price", ascending=True)

    data["cumulative_quantity"] = data["quantity"].cumsum()
    return data


def create_orderbook_figure(snapshot: dict, levels: int = 100) -> go.Figure:
    bids = build_orderbook_side(snapshot, "bids", levels)
    asks = build_orderbook_side(snapshot, "asks", levels)

    if bids.empty and asks.empty:
        raise ValueError("Snapshot does not contain bids or asks data.")

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.14,
        row_heights=[0.65, 0.35],
        subplot_titles=(
            "Cumulative order book depth",
            f"Top {levels} level size by price",
        ),
    )

    if not bids.empty:
        fig.add_trace(
            go.Scatter(
                x=bids["price"],
                y=bids["cumulative_quantity"],
                mode="lines",
                name="Bid depth",
                line={"color": "#00cc96", "width": 2},
                fill="tozeroy",
                fillcolor="rgba(0, 204, 150, 0.22)",
                hovertemplate=(
                    "Bid price: %{x:.8f}<br>"
                    "Cumulative quantity: %{y:,.2f}<extra></extra>"
                ),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Bar(
                x=bids["price"],
                y=bids["quantity"],
                name="Bid size",
                marker_color="#00cc96",
                opacity=0.75,
                hovertemplate=(
                    "Bid price: %{x:.8f}<br>"
                    "Quantity: %{y:,.2f}<extra></extra>"
                ),
            ),
            row=2,
            col=1,
        )

    if not asks.empty:
        fig.add_trace(
            go.Scatter(
                x=asks["price"],
                y=asks["cumulative_quantity"],
                mode="lines",
                name="Ask depth",
                line={"color": "#ef553b", "width": 2},
                fill="tozeroy",
                fillcolor="rgba(239, 85, 59, 0.22)",
                hovertemplate=(
                    "Ask price: %{x:.8f}<br>"
                    "Cumulative quantity: %{y:,.2f}<extra></extra>"
                ),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Bar(
                x=asks["price"],
                y=asks["quantity"],
                name="Ask size",
                marker_color="#ef553b",
                opacity=0.75,
                hovertemplate=(
                    "Ask price: %{x:.8f}<br>"
                    "Quantity: %{y:,.2f}<extra></extra>"
                ),
            ),
            row=2,
            col=1,
        )

    best_bid = None if bids.empty else bids["price"].max()
    best_ask = None if asks.empty else asks["price"].min()
    title_parts = ["Order Book Visualization"]

    if best_bid is not None:
        title_parts.append(f"Best bid: {best_bid:.8f}")
    if best_ask is not None:
        title_parts.append(f"Best ask: {best_ask:.8f}")
    if best_bid is not None and best_ask is not None:
        mid_price = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
        title_parts.append(f"Spread: {spread:.8f}")
        fig.add_vline(
            x=mid_price,
            line_width=1,
            line_dash="dash",
            line_color="#ab63fa",
            annotation_text="mid",
            annotation_position="top",
            row=1,
            col=1,
        )

    fig.update_layout(
        title=" | ".join(title_parts),
        template="plotly_dark",
        height=800,
        barmode="overlay",
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    fig.update_xaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Cumulative quantity", row=1, col=1)
    fig.update_xaxes(title_text="Price", row=2, col=1)
    fig.update_yaxes(title_text="Quantity", row=2, col=1)

    return fig


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a Plotly order book visualization from an orderbook.py snapshot file."
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Snapshot file to read. Defaults to the latest *-snapshots-*.txt file.",
    )
    parser.add_argument(
        "--snapshot-index",
        type=int,
        default=-1,
        help="Line/snapshot index to visualize. Defaults to -1, the latest snapshot in the file.",
    )
    parser.add_argument(
        "--levels",
        type=int,
        default=100,
        help="Number of bid/ask price levels to plot from the selected snapshot.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("orderbook_visualization.html"),
        help="HTML file to write.",
    )
    args = parser.parse_args()

    snapshot_file = args.file or find_latest_snapshot_file()
    snapshot = load_snapshot(snapshot_file, args.snapshot_index)
    figure = create_orderbook_figure(snapshot, args.levels)
    figure.write_html(args.output, include_plotlyjs="cdn")

    print(f"Wrote order book visualization to {args.output}")
    print(f"Source snapshot file: {snapshot_file}")


if __name__ == "__main__":
    main()
