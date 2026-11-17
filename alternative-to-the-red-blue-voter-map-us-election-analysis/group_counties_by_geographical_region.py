import polars as pl
import plotly.express as px

# 1. Official Texas Comptroller 12 Economic Regions (all 254 counties):
TEXAS_REGIONS = {
    "Alamo": [
        "Atascosa", "Bandera", "Bexar", "Calhoun", "Comal", "DeWitt", "Frio",
        "Gillespie", "Goliad", "Gonzales", "Guadalupe", "Jackson", "Karnes",
        "Kendall", "Kerr", "Lavaca", "Medina", "Victoria", "Wilson",
    ],
    "Capital": [
        "Bastrop", "Blanco", "Burnet", "Caldwell", "Fayette", "Hays", "Lee",
        "Llano", "Travis", "Williamson",
    ],
    "Central Texas": [
        "Bell", "Bosque", "Brazos", "Burleson", "Coryell", "Falls", "Freestone",
        "Grimes", "Hamilton", "Hill", "Lampasas", "Leon", "Limestone",
        "Madison", "McLennan", "Milam", "Mills", "Robertson", "San Saba",
        "Washington",
    ],
    "Gulf Coast": [
        "Austin", "Brazoria", "Chambers", "Colorado", "Fort Bend", "Galveston",
        "Harris", "Liberty", "Matagorda", "Montgomery", "Walker", "Waller",
        "Wharton",
    ],
    "High Plains": [
        "Armstrong", "Bailey", "Briscoe", "Carson", "Castro", "Childress",
        "Cochran", "Collingsworth", "Crosby", "Dallam", "Deaf Smith", "Dickens",
        "Donley", "Floyd", "Garza", "Gray", "Hale", "Hall", "Hansford",
        "Hartley", "Hemphill", "Hockley", "Hutchinson", "King", "Lamb",
        "Lipscomb", "Lubbock", "Lynn", "Moore", "Motley", "Ochiltree",
        "Oldham", "Parmer", "Potter", "Randall", "Roberts", "Sherman",
        "Swisher", "Terry", "Wheeler", "Yoakum",
    ],
    "Metroplex": [
        "Collin", "Cooke", "Dallas", "Denton", "Ellis", "Erath", "Fannin",
        "Grayson", "Hood", "Hunt", "Johnson", "Kaufman", "Navarro",
        "Palo Pinto", "Parker", "Rockwall", "Somervell", "Tarrant", "Wise",
    ],
    "Northwest": [
        "Archer", "Baylor", "Brown", "Callahan", "Clay", "Coleman", "Comanche",
        "Cottle", "Eastland", "Fisher", "Foard", "Hardeman", "Haskell", "Jack",
        "Jones", "Kent", "Knox", "Mitchell", "Montague", "Nolan", "Runnels",
        "Scurry", "Shackelford", "Stephens", "Stonewall", "Taylor",
        "Throckmorton", "Wichita", "Wilbarger", "Young",
    ],
    "South Texas": [
        "Aransas", "Bee", "Brooks", "Cameron", "Dimmit", "Duval", "Edwards",
        "Hidalgo", "Jim Hogg", "Jim Wells", "Kenedy", "Kinney", "Kleberg",
        "La Salle", "Live Oak", "Maverick", "McMullen", "Nueces", "Real",
        "Refugio", "San Patricio", "Starr", "Uvalde", "Val Verde", "Webb",
        "Willacy", "Zapata", "Zavala",
    ],
    "Southeast": [
        "Angelina", "Hardin", "Houston", "Jasper", "Jefferson", "Nacogdoches",
        "Newton", "Orange", "Polk", "Sabine", "San Augustine", "San Jacinto",
        "Shelby", "Trinity", "Tyler",
    ],
    "Upper East": [
        "Anderson", "Bowie", "Camp", "Cass", "Cherokee", "Delta", "Franklin",
        "Gregg", "Harrison", "Henderson", "Hopkins", "Lamar", "Marion",
        "Morris", "Panola", "Rains", "Red River", "Rusk", "Smith", "Titus",
        "Upshur", "Van Zandt", "Wood",
    ],
    "Upper Rio Grande": [
        "Brewster", "Culberson", "El Paso", "Hudspeth", "Jeff Davis", "Presidio",
    ],
    "West Texas": [
        "Andrews", "Borden", "Coke", "Concho", "Crane", "Crockett", "Dawson",
        "Ector", "Gaines", "Glasscock", "Howard", "Irion", "Kimble", "Loving",
        "Martin", "Mason", "McCulloch", "Menard", "Midland", "Pecos", "Reagan",
        "Reeves", "Schleicher", "Sterling", "Sutton", "Terrell", "Tom Green",
        "Upton", "Ward", "Winkler",
    ],
}

COUNTY_TO_REGION = {county: region
                    for region, counties in TEXAS_REGIONS.items()
                    for county in counties}

# 2. Load and clean data (read as strings; Polars has no `thousands=` option):
MARGIN_RE = r"^\s*([RD])\s*\+?\s*([\d.]+)"
region_lookup_lower = {k.lower(): v for k, v in COUNTY_TO_REGION.items()}

df = (
    pl.read_csv("https://bit.ly/48jF7Zi",
                columns=["County", "Population", "Vote Margin"],
                infer_schema=False)
    .with_columns(
        pl.col("Population").str.replace_all(",", "").cast(pl.Int64),
        pl.col("County").str.replace(r"\s+County$", "").str.strip_chars()
          .alias("County_Short"),
        # Vectorized margin parsing (won't crash on "Even" or missing "+"):
        (pl.col("Vote Margin").str.extract(MARGIN_RE, 1)
           .replace_strict({"R": -1.0, "D": 1.0}, default=0.0)
         * pl.col("Vote Margin").str.extract(MARGIN_RE, 2)
           .cast(pl.Float64, strict=False).fill_null(0.0))
        .alias("Margin_Numeric"),
    )
    # Map each county to its region (case-insensitive):
    .with_columns(
        pl.col("County_Short").str.to_lowercase()
          .replace_strict(region_lookup_lower, default="Other")
          .alias("Region"),
    )
)

max_margin = df["Margin_Numeric"].abs().max()

# 3. Build the hierarchical treemap: All Counties -> Region -> County:
fig = px.treemap(
    df,
    path=[px.Constant("All Counties"), "Region", "County_Short"],
    values="Population",
    color="Margin_Numeric",
    color_continuous_scale="RdBu",
    color_continuous_midpoint=0,
    range_color=[-max_margin, max_margin],
    custom_data=["Vote Margin", "County"]
)

# Populate parent region headers/tooltips with population-weighted margins.
# Parent nodes (root and regions) have ids with fewer than two "/"; Plotly
# fills their customdata with "(?)" placeholders.
trace = fig.data[0]
customdata = trace.customdata.copy()
for idx, (node_id, label, val) in enumerate(
    zip(trace.ids, trace.labels, trace.marker.colors)
):
    if node_id.count("/") < 2:
        if val > 0:
            fmt_margin = f"D +{val:.1f} (pop-weighted)"
        elif val < 0:
            fmt_margin = f"R +{abs(val):.1f} (pop-weighted)"
        else:
            fmt_margin = "Even"
        customdata[idx, 0] = fmt_margin
        customdata[idx, 1] = (label if label == "All Counties"
                              else f"{label} Region")
trace.customdata = customdata

# 4. Format cells, borders, and hover tooltips:
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
        "Vote Margin: %{customdata[0]}<extra></extra>"
    ),
    tiling=dict(pad=2),
    marker=dict(
        # Dark charcoal border makes region edges pop against light/white tiles
        line=dict(width=1.0, color="#222222"),
        # Thicken the colored frame around each region's county cluster:
        pad=dict(t=26, l=6, r=6, b=6)
    ),
)

# 5. Set layout & export:
fig.update_layout(
    title=dict(
        text="Texas County Population & Senate Race Vote Margin (%) 2026 by Region",
        x=0.5,
    ),
    width=1100,
    height=950,
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
    uniformtext=dict(minsize=10, mode="hide"),
    margin=dict(t=60, l=20, r=20, b=100),
)

fig.write_image("plot_by_region.svg")
fig.show()  # auto-detects: browser for scripts, inline in Jupyter
