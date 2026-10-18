import numpy as np
import matplotlib.pyplot as plt
import pymc as pm
from scipy.optimize import curve_fit

# Logistic Growth Model:
def logistic_model(t, L, k, t0):
    return L / (1.0 + np.exp(-k * (t - t0)))

def fit_logistic(years, population, initial_guess, param_bounds):
    """Fit the logistic model and return fitted parameters plus fit metrics."""
    popt, pcov = curve_fit(logistic_model, years, population,
                           p0=initial_guess, bounds=param_bounds)

    # Standard errors (1-sigma) from covariance matrix:
    perr = np.sqrt(np.diag(pcov))

    # Goodness-of-Fit Metrics (R² and RMSE):
    residuals = population - logistic_model(years, *popt)
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((population - np.mean(population)) ** 2)
    r_squared = 1.0 - (ss_res / ss_tot)
    rmse = np.sqrt(np.mean(residuals**2))

    return popt, perr, r_squared, rmse


def plot_fit(country, years, population, popt, data_range, xlim, ylim, output_file,
             fit_label='Logistic Fit', title_suffix='Logistic Model Fit',
             curve_samples=None):
    """Plot census data against the fitted logistic curve and save the figure.

    curve_samples: optional (n_samples, n_years) array of posterior predictive
    curves; when given, a 94% credible interval band is drawn.
    """
    L_fit = popt[0]

    # Domain for future projection:
    years_future = np.linspace(years[0], 2200, 400)
    population_fit = logistic_model(years_future, *popt)

    plt.figure(figsize=(10, 6))
    plt.scatter(years, population, label=f'{country} Census Data', color='red')
    if curve_samples is not None:
        lower, upper = np.percentile(curve_samples, [3, 97], axis=0)
        plt.fill_between(years_future, lower, upper, color='blue', alpha=0.2,
                         label='94% Credible Interval')
    plt.plot(years_future, population_fit,
             label=f'{fit_label}\nMax Pop (L) = {L_fit:.2f} Million', color='blue')
    plt.title(f'{country} Population Growth: {title_suffix} ({data_range} Data)')
    plt.xlabel('Year')
    plt.ylabel('Population (Millions)')
    plt.axhline(L_fit, color='gray', linestyle='--',
                label='Estimated Maximum (Carrying Capacity)')
    plt.xlim(*xlim)
    plt.ylim(*ylim)
    plt.legend(loc="upper left")
    plt.grid(True, alpha=0.5)
    plt.tight_layout()

    plt.savefig(output_file)
    plt.show()


def population_prediction(country, years, population, initial_guess, param_bounds,
                          data_range, xlim, ylim, output_file):
    popt, perr, r_squared, rmse = fit_logistic(years, population,
                                               initial_guess, param_bounds)
    L_fit, k_fit, t0_fit = popt

    plot_fit(country, years, population, popt, data_range, xlim, ylim, output_file)

    print(f"--- {country} ---")
    print(f"Fitted Maximum Population (L): {L_fit:.2f} million")
    print(f"Growth Rate (k): {k_fit:.4f}")
    print(f"Midpoint Year (t0): {t0_fit:.1f}")
    print(f"R²: {r_squared:.4f}")
    print(f"RMSE: {rmse:.4f}")


def fit_logistic_bayes(years, population, priors, draws=2000, tune=2000):
    """Fit the logistic model with Bayesian inference (PyMC NUTS sampling).

    priors: dict with 'L', 'k', 't0' (lower/upper tuples for Uniform priors)
    and 'sigma' (HalfNormal scale).
    Returns the InferenceData posterior samples.
    """
    with pm.Model() as model:
        L = pm.Uniform('L', *priors['L'])
        k = pm.Uniform('k', *priors['k'])
        t0 = pm.Uniform('t0', *priors['t0'])
        sigma = pm.HalfNormal('sigma', priors['sigma'])

        mu = L / (1.0 + pm.math.exp(-k * (years - t0)))
        pm.Normal('obs', mu=mu, sigma=sigma, observed=population)

        idata = pm.sample(draws=draws, tune=tune, chains=4, cores=1,
                          target_accept=0.95, progressbar=False, random_seed=42)

    return idata


def population_prediction_bayes(country, years, population, priors,
                                data_range, xlim, ylim, output_file):
    idata = fit_logistic_bayes(years, population, priors)
    post = idata.posterior

    # Posterior mean as point estimate:
    popt = [float(post[v].mean()) for v in ('L', 'k', 't0')]
    L_fit, k_fit, t0_fit = popt

    # Posterior predictive curves over the projection domain:
    years_future = np.linspace(years[0], 2200, 400)
    L_s = post['L'].values.ravel()
    k_s = post['k'].values.ravel()
    t0_s = post['t0'].values.ravel()
    curve_samples = logistic_model(years_future[None, :],
                                   L_s[:, None], k_s[:, None], t0_s[:, None])

    plot_fit(country, years, population, popt, data_range, xlim, ylim, output_file,
             fit_label='Bayesian Logistic Fit',
             title_suffix='Bayesian Logistic Model Fit',
             curve_samples=curve_samples)

    # 94% highest density interval for each parameter:
    hdi = {v: np.percentile(post[v].values, [3, 97]) for v in ('L', 'k', 't0')}

    print(f"--- {country} (Bayesian) ---")
    print(f"Max Population (L): {L_fit:.2f} million  [94% HDI: {hdi['L'][0]:.2f}, {hdi['L'][1]:.2f}]")
    print(f"Growth Rate (k): {k_fit:.4f}  [94% HDI: {hdi['k'][0]:.4f}, {hdi['k'][1]:.4f}]")
    print(f"Midpoint Year (t0): {t0_fit:.1f}  [94% HDI: {hdi['t0'][0]:.1f}, {hdi['t0'][1]:.1f}]")


def us_population_prediction():
    # US Decennial Census Data, population in millions:
    years = np.array([1790, 1800, 1810, 1820, 1830, 1840, 1850, 1860,
            1870, 1880, 1890, 1900, 1910, 1920, 1930, 1940,
            1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020],
            dtype=float)

    population = np.array([3.929, 5.308, 7.239, 9.638, 12.866, 17.069,
                        23.191, 31.443, 38.558, 50.189, 62.979, 76.212,
                        92.228, 106.021, 123.202, 132.164, 151.325, 179.323,
                        203.302, 226.542, 248.709, 281.421, 308.745, 331.449],
                        dtype=float)

    population_prediction(
        country='US',
        years=years,
        population=population,
        initial_guess=[500, 0.03, 1900],
        param_bounds=(0, [2000, 0.5, 2200]),
        data_range='1790-2020',
        xlim=(1780, 2200),
        ylim=(0, 505),
        output_file='us_pop_logistic.png',
    )


def india_population_prediction():
    # India Population Data, population in millions:
    years = np.array([1951, 1961, 1971, 1981, 1991, 2001, 2011, 2021], dtype=float)
    population = np.array([361, 439, 548, 683, 846, 1028, 1210, 1393], dtype=float)

    population_prediction(
        country='India',
        years=years,
        population=population,
        initial_guess=[2000, 0.03, 2000],
        param_bounds=(0, [5000, 0.5, 2200]),
        data_range='1951-2021',
        xlim=(1950, 2200),
        ylim=(0, 5000),
        output_file='india_pop_logistic.png',
    )


def us_population_prediction_bayes():
    # US Decennial Census Data, population in millions:
    years = np.array([1790, 1800, 1810, 1820, 1830, 1840, 1850, 1860,
            1870, 1880, 1890, 1900, 1910, 1920, 1930, 1940,
            1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020],
            dtype=float)

    population = np.array([3.929, 5.308, 7.239, 9.638, 12.866, 17.069,
                        23.191, 31.443, 38.558, 50.189, 62.979, 76.212,
                        92.228, 106.021, 123.202, 132.164, 151.325, 179.323,
                        203.302, 226.542, 248.709, 281.421, 308.745, 331.449],
                        dtype=float)

    population_prediction_bayes(
        country='US',
        years=years,
        population=population,
        priors={'L': (331, 2000), 'k': (0.001, 0.5), 't0': (1790, 2200),
                'sigma': 50},
        data_range='1790-2020',
        xlim=(1780, 2200),
        ylim=(0, 505),
        output_file='us_pop_logistic_bayes.png',
    )


def india_population_prediction_bayes():
    # India Population Data, population in millions:
    years = np.array([1951, 1961, 1971, 1981, 1991, 2001, 2011, 2021], dtype=float)
    population = np.array([361, 439, 548, 683, 846, 1028, 1210, 1393], dtype=float)

    population_prediction_bayes(
        country='India',
        years=years,
        population=population,
        priors={'L': (1393, 5000), 'k': (0.001, 0.5), 't0': (1951, 2200),
                'sigma': 100},
        data_range='1951-2021',
        xlim=(1950, 2200),
        ylim=(0, 5000),
        output_file='india_pop_logistic_bayes.png',
    )


if __name__ == "__main__":
    us_population_prediction()
    india_population_prediction()
    us_population_prediction_bayes()
    india_population_prediction_bayes()
    