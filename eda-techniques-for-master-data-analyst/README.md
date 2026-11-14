# EDA Techniques for Master Data Analysts

Exploratory data analysis of a synthetic `humans.csv` dataset (Height, Weight, Age, Gender)
using Polars and Seaborn: univariate, bivariate and multivariate analysis, plus an engineered
BMI feature.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
```

## Notebook

Open `eda-techniques-4-data-analyst.ipynb` and select the `.venv` interpreter as the kernel.

1. Download and load the CSV with Polars.
2. Univariate: box plot of Height.
3. Bivariate: scatter plot of Height vs. Weight.
4. Multivariate: pairplot of Height, Weight and Age.
5. Feature engineering: BMI = Weight / (Height / 100)², plotted as a histogram.

## Layout

| Path | Purpose |
| --- | --- |
| `main.py` | Downloads the dataset into `data/` |
| `eda-techniques-4-data-analyst.ipynb` | The analysis |
| `data/humans.csv` | Dataset (generated, not tracked) |
