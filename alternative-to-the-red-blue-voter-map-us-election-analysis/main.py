import polars as pl
import plotly.express as px

# 1. Load and clean data (read as strings; Polars has no `thousands=` option):
MARGIN_RE = r"^\s*([RD])\s*\+?\s*([\d.]+)"
df = (
    pl.read_csv("https://bit.ly/48jF7Zi",
                columns=["County", "Population", "Vote Margin"],
                infer_schema=False)
    .with_columns(
        # Strip thousands separators, then cast to integer:
        pl.col("Population").str.replace_all(",", "").cast(pl.Int64),
        # Strip trailing " County" in county names:
        pl.col("County").str.replace(r"\s+County$", "").str.strip_chars()
          .alias("County_Short"),
        # Parse margin (won't crash on "Even" or missing "+"):
        (pl.col("Vote Margin").str.extract(MARGIN_RE, 1)
           .replace_strict({"R": -1.0, "D": 1.0}, default=0.0)
         * pl.col("Vote Margin").str.extract(MARGIN_RE, 2)
           .cast(pl.Float64, strict=False).fill_null(0.0))
        .alias("Margin_Numeric"),
    )
)

max_margin = df["Margin_Numeric"].abs().max()

# 2. Build the treemap:
fig = px.treemap(df,
                 path=[px.Constant("All Counties"), "County_Short"],
                 values="Population",
                 color="Margin_Numeric",
                 color_continuous_scale="RdBu",
                 color_continuous_midpoint=0,
                 range_color=[-max_margin, max_margin],
                 custom_data=["Vote Margin", "County"])

# 3. Format cells, borders, and hover tooltips:
fig.update_traces(
    texttemplate=(
        "<b>%{label}</b><br>"
        "<span style='font-size:0.8em'>"
        "%{customdata[0]}"
        "</span>"
    ),
    textposition="middle center",
    hovertemplate=(
        "<b>%{customdata[1]}</b><br>"
        "Population: %{value:,}<br>"
        "Vote Margin: %{customdata[0]}"
        "<extra></extra>"
    ),
    tiling=dict(pad=0),
    marker=dict(
        line=dict(width=0.5, color="white"),
        pad=dict(t=22, l=0, r=0, b=0),
    )
)

# 4. Layout & export treemap:
fig.update_layout(
    title=dict(
        text="Texas County Population & Senate Race Vote Margin (%) 2026",
        x=0.5),
    width=850,
    height=850,
    coloraxis_colorbar=dict(
        orientation="h",
        x=0.5,
        xanchor="center",
        y=-0.03,
        yanchor="top",
        len=0.75,
        thickness=18,
        title=dict(text="Vote Margin", side="bottom"),
        tickvals=[-80, -40, 0, 40, 80],
        ticktext=["R +80", "R +40", "Even", "D +40", "D +80"],
    ),
    uniformtext=dict(minsize=15, mode="hide"),
    margin=dict(t=60, l=20, r=20, b=100)
)

fig.write_image("plot.svg")
fig.show()  # auto-detects: browser for scripts, inline in Jupyter
