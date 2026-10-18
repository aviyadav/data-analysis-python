# Predicting Population Growth with Python

Fits a **logistic growth model** to historical census data to estimate a country's
carrying capacity (maximum population), growth rate, and midpoint year, and projects
population growth out to the year 2200.

Two fitting approaches are implemented:

- **Frequentist** — nonlinear least squares via `scipy.optimize.curve_fit`
- **Bayesian** — full posterior inference via PyMC (NUTS sampler), giving
  credible intervals for every parameter and a posterior predictive band on the plot

Currently includes analyses for:

- **United States** — decennial census data, 1790–2020 (24 data points)
- **India** — census data, 1951–2021 (8 data points)

## The Logistic Model

Population growth is modeled with the logistic function:

$$
P(t) = \frac{L}{1 + e^{-k\,(t - t_0)}}
$$

Where:

| Symbol | Meaning |
|--------|---------|
| $L$    | Carrying capacity (maximum population, in millions) |
| $k$    | Growth rate |
| $t_0$  | Midpoint year (inflection point of fastest growth) |

For the frequentist fit, parameters are estimated with `scipy.optimize.curve_fit`
using physically meaningful bounds; fit quality is reported as R² and RMSE.

For the Bayesian fit, the same logistic equation is expressed as a probabilistic
model with uniform priors on $L$, $k$, and $t_0$ and a HalfNormal prior on the
observation noise $\sigma$:

$$
y_t \sim \mathcal{N}\!\left(\frac{L}{1 + e^{-k\,(t - t_0)}},\ \sigma\right)
$$

Sampling uses NUTS (4 chains, 2000 tune + 2000 draws, `target_accept=0.95`).
Results are reported as posterior means with 94% highest density intervals (HDI).

## Results

Frequentist (least squares):

| Country | Max Population (L) | Growth Rate (k) | Midpoint Year (t₀) | R² | RMSE |
|---------|-------------------:|----------------:|-------------------:|---:|-----:|
| US      | ~499 million       | 0.0206          | 1988               | 0.998 | 4.70 |
| India   | ~2769 million      | 0.0280          | 2020               | 0.999 | 7.50 |

Bayesian (posterior mean, 94% HDI):

| Country | Max Population (L) | Growth Rate (k) | Midpoint Year (t₀) |
|---------|-------------------:|----------------:|-------------------:|
| US      | ~505 million [451, 577] | 0.0205 [0.019, 0.022] | 1989 [1977, 2003] |
| India   | ~2941 million [2364, 4070] | 0.0276 [0.024, 0.031] | 2024 [2010, 2047] |

The script saves two plots per country showing the census data, the fitted curve,
and the estimated carrying capacity (Bayesian plots add a 94% credible interval band):

- `us_pop_logistic.png` / `us_pop_logistic_bayes.png`
- `india_pop_logistic.png` / `india_pop_logistic_bayes.png`

## Requirements

- Python >= 3.14
- numpy, scipy, matplotlib, pymc (see [pyproject.toml](./pyproject.toml))

## Usage

With [uv](https://docs.astral.sh/uv/):

```bash
uv run main.py
```

Or with pip:

```bash
pip install numpy scipy matplotlib
python main.py
```

## Project Structure

- [main.py](./main.py) — the entire analysis:
  - `logistic_model` — the logistic growth function
  - `fit_logistic` — frequentist parameter fitting and goodness-of-fit metrics (R², RMSE)
  - `fit_logistic_bayes` — Bayesian fitting with PyMC (NUTS sampling)
  - `plot_fit` — plots census data vs. the fitted curve (with optional credible
    interval band) and saves the figure
  - `population_prediction` / `population_prediction_bayes` — shared fit → plot → report pipelines
  - `us_population_prediction` / `india_population_prediction` — country data and config (frequentist)
  - `us_population_prediction_bayes` / `india_population_prediction_bayes` — country data, priors and config (Bayesian)

## Adding Another Country

Add a function that supplies the census data and fit configuration, then call the
shared `population_prediction` pipeline:

```python
def canada_population_prediction():
    years = np.array([...], dtype=float)        # census years
    population = np.array([...], dtype=float)   # population in millions

    population_prediction(
        country='Canada',
        years=years,
        population=population,
        initial_guess=[100, 0.03, 2000],
        param_bounds=(0, [500, 0.5, 2200]),
        data_range='1871-2021',
        xlim=(1870, 2200),
        ylim=(0, 100),
        output_file='canada_pop_logistic.png',
    )
```

For the Bayesian version, supply priors instead of an initial guess:

```python
def canada_population_prediction_bayes():
    years = np.array([...], dtype=float)
    population = np.array([...], dtype=float)

    population_prediction_bayes(
        country='Canada',
        years=years,
        population=population,
        priors={'L': (40, 500), 'k': (0.001, 0.5), 't0': (1871, 2200),
                'sigma': 20},
        data_range='1871-2021',
        xlim=(1870, 2200),
        ylim=(0, 100),
        output_file='canada_pop_logistic_bayes.png',
    )
```
