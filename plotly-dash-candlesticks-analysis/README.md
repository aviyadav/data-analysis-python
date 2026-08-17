# Plotly Dash Candlesticks Analysis

A Python project demonstrating cryptocurrency data visualization and real-time order book collection using Binance APIs. This repository contains two examples: a live candlestick chart dashboard and an order book data collector.

## Overview

This codebase provides tools for analyzing cryptocurrency market data from Binance:

- **Candlestick Dashboard**: Interactive web application for visualizing price movements and technical indicators
- **Order Book Collector**: WebSocket-based tool for capturing real-time order book snapshots and updates
- **Order Book Visualization**: Plotly depth chart generated from saved order book snapshot files

## Technologies Used

- **Dash & dash-bootstrap-components**: Web UI framework with Bootstrap styling
- **Plotly**: Interactive candlestick and line charts
- **pandas & pandas-ta**: Data manipulation and technical analysis indicators (RSI)
- **requests & httpx**: HTTP client for REST API calls
- **websockets**: Real-time data streaming from Binance WebSocket
- **aiofiles**: Async file I/O for high-performance data logging

## Requirements

- Python 3.13 or newer
- `uv` package manager

## Installation

From the project root:

```bash
uv sync
```

## Examples

### 1. Candlestick Dashboard (`example.py`)

An interactive Dash web application that displays live candlestick charts with RSI indicators.

**Features:**
- Select market pairs: BTCUSDT, ETHUSDT, or XRPUSDT
- Switch between timeframes: 1m (1 minute), 1h (1 hour), 1d (1 day)
- Choose number of bars to display: 20, 50, or 100
- Interactive range slider to zoom into specific time periods
- Real-time updates every 2 seconds
- Candlestick chart with OHLC (Open, High, Low, Close) data
- RSI (Relative Strength Index) indicator chart below the candlesticks
- Dark theme (Cyborg) for better visibility

**Data Source:**
Binance public klines (candlestick) endpoint: `https://api.binance.com/api/v3/klines`

**Run the dashboard:**

```bash
uv run python example.py
```

The Dash development server will start and display a local URL (typically `http://127.0.0.1:8050/`). Open this URL in your browser to view the dashboard.

---

### 2. Order Book Collector (`orderbook.py`)

An asynchronous WebSocket client that captures real-time order book data from Binance.

**Features:**
- Fetches initial order book snapshot via REST API (up to 5000 levels)
- Connects to Binance WebSocket stream for real-time order book updates
- Saves snapshots and updates to dated text files
- Async I/O for efficient data capture
- Continuous data collection until manually stopped

**Data Source:**
- REST API: `https://api.binance.com/api/v3/depth` (initial snapshot)
- WebSocket: `wss://stream.binance.com:9443/ws/{pair}@depth` (live updates)

**Output Files:**
- `{pair}-snapshots-{date}.txt`: Initial order book snapshot with timestamp
- `{pair}-updates-{date}.txt`: Streaming order book updates (one JSON per line)

**Run the order book collector:**

```bash
uv run python orderbook.py
```

By default, this collects data for the UNIUSDT pair. To collect data for a different pair, modify the last line in `orderbook.py`:

```python
asyncio.run(orderbook_download("BTCUSDT"))  # Change to desired pair
```

Press `Ctrl+C` to stop the data collection.

---

### 3. Order Book Visualization (`orderbook_visualization.py`)

A Plotly script that reads the newline-delimited JSON snapshot file created by `orderbook.py` and generates an interactive HTML order book visualization.

**Features:**
- Reads the latest `{pair}-snapshots-{date}.txt` file by default
- Plots cumulative bid and ask depth
- Shows per-price-level bid and ask sizes
- Marks the mid price and includes best bid, best ask, and spread in the chart title
- Writes a standalone `orderbook_visualization.html` file

**Run the visualization:**

```bash
uv run python orderbook_visualization.py
```

By default, the script finds the most recently modified `*-snapshots-*.txt` file in the project root, visualizes the latest snapshot in that file, and writes `orderbook_visualization.html`.

To visualize a specific file or change the number of levels:

```bash
uv run python orderbook_visualization.py --file uniusdt-snapshots-2026-08-18.txt --levels 200
```

Other useful options:

```bash
uv run python orderbook_visualization.py --snapshot-index 0 --output first_snapshot.html
uv run python orderbook_visualization.py --snapshot-index -1 --output latest_snapshot.html
```

Open the generated HTML file in your browser to view the interactive chart. Generated visualization HTML files are local outputs and are not required for source control.

## Project Structure

```
.
├── example.py              # Candlestick dashboard application
├── orderbook.py            # Order book data collector
├── orderbook_visualization.py  # Order book depth visualization
├── pyproject.toml          # Project dependencies and metadata
├── README.md               # This file
├── src/
│   └── plotly_dash_candlesticks_analysis/
│       └── __init__.py     # Package placeholder
└── *.txt                   # Generated order book data files
```

## Notes

- The package entry point in `pyproject.toml` is currently a placeholder. Run the example scripts directly.
- The candlestick dashboard auto-refreshes every 2 seconds to show the latest market data.
- Order book data files can grow large during extended collection periods.
- Generated visualization HTML files can be recreated from snapshot files.
- Both examples use Binance's public API endpoints and do not require authentication.

## Future Enhancements

Potential improvements for this project:
- Add more technical indicators (MACD, Bollinger Bands, EMA)
- Support for additional cryptocurrency exchanges
- Real-time order book visualization dashboard
- Historical data analysis and backtesting capabilities
- Database storage for order book data instead of text files
