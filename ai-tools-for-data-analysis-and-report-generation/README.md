

## 1. Lumen AI

```bash
sudo pacman -S ollama

sudo systemctl enable --now ollama.service

sudo systemctl status ollama.service

ollama run qwen3.5:9b
```


```bash
uv run lumen-ai serve data/sales_data.csv --provider ollama
```

http://localhost:5006/lumen_ai


Query - “Show total net revenue for each month as a line chart.”



Stop and clean up
```bash

ollama stop qwen3.5:9b

ollama rm qwen3.5:9b

sudo systemctl stop ollama.service
```

## 2. Data Formulator

```bash
uv add data_formulator

uv run python data_formulator
```

http://127.0.0.1:5567/

## 3. DB-GPT

DB-GPT pins `aiohttp==3.8.4`, which conflicts with Lumen. Install it in an
isolated tool environment with Python 3.11 instead of adding it to this project.

```bash
uv tool install --python 3.11 --with-executables-from dbgpt dbgpt-app

dbgpt start webserver
```



### Others

Lumen for data exploration and narrative reports.
Data Formulator for visual analysis and reports.
DB-GPT for SQL and Python analysis.
Vizro-MCP for creating interactive Python dashboards.
DeepAnalyze for autonomous analysis and research reports.
