# imports
import logging
import numpy as np
from scipy import integrate
from statsmodels.distributions.copula.api import (
    GaussianCopula,
    StudentTCopula,
    ClaytonCopula,
    FrankCopula,
    GumbelCopula,
)

logger = logging.getLogger(__name__)

def get_copula_families(copula_families: list) -> list:
    """Retrieve copula families from configuration."""
    logger.debug(f"Retrieving copula families from configuration: {copula_families}.")

    copula_database = {
        "Gaussian": lambda param=None: GaussianCopula(corr=param),
        "t": lambda param=None: StudentTCopula(corr=param, df=4),
        "Clayton": lambda param=None: ClaytonCopula(theta=param),
        "Gumbel": lambda param=None: GumbelCopula(theta=param),
        "Frank": lambda param=None: FrankCopula(theta=param)
    }

    # Select copula families based on config
    selected_families = {}
    logger.debug(f"Configured families: {copula_families}")

    for family in copula_families:
        if family not in copula_database:
            error_msg = f"Unsupported copula family: {family}. Supported families are: {list(copula_database.keys())}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        selected_families[family] = copula_database[family]
        logger.debug(f"Selected copula family: {family}")

    return selected_families


def get_integration_scheme(scheme: str, **kwargs) -> callable:
    """Retrieve integration scheme based on configuration."""
    logger.debug(f"Retrieving integration scheme: {scheme}")

    def _adaptive_2d_quadrature(f: callable, a: float, b: float, c: callable, d: callable) -> float:
        '''Adaptive 2D quadrature over v in [c(t), d(t)] then t in [a, b].'''
        logger.debug("Starting adaptive 2D quadrature.")

        # Define lower and upper bounds for inner integral
        def lower(t):
            return float(np.asarray(c(t), dtype=float).item())

        def upper(t):
            return float(np.asarray(d(t), dtype=float).item())
        
        # Wrap the function to ensure it returns float
        # f = lambda v, t: float(f(v, t))

        # Perform double integration
        result, error = integrate.dblquad(f, a, b, lower, upper, **kwargs)
        logger.debug(f"Adaptive 2D quadrature result: {result} (error: {error})")

        return result


    def _monte_carlo_integration(f: callable, a: float, b: float, c: callable, d: callable) -> float:
        '''Monte Carlo integration over v in [c(t), d(t)] then t in [a, b].'''
        logger.debug(f"Starting Monte Carlo integration. Samples: {kwargs['n_samples']}, Random State: {kwargs['random_state']}")

        # Generate samples
        rng = np.random.default_rng(kwargs["random_state"])
        t_samples = rng.uniform(a, b, size=kwargs["n_samples"])
        c_vals = c(t_samples)
        d_vals = d(t_samples)
        v_samples = rng.uniform(c_vals, d_vals)

        # Evaluate function at samples
        f_vals = f(v_samples, t_samples)
        volumes = (b - a) * (d_vals - c_vals)

        # Compute mean of function values weighted by volumes
        result = np.mean(volumes * f_vals)
        logger.debug(f"Monte Carlo integration result: {result}")
        return result

    schemes = {
        "ADAPTIVE_2D_QUADRATURE": _adaptive_2d_quadrature,
        "MONTE_CARLO": _monte_carlo_integration
    }

    if scheme not in schemes:
        error_msg = f"Unsupported integration scheme: {scheme}. Supported schemes are: {list(schemes.keys())}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    return schemes[scheme]


def get_runoff_integration_bounds(v0, params, v0_limit=100.0) -> list:
    '''Determine integration bounds for runoff volume v0 based on physical model parameters.'''
    logger.debug(f"Calculating runoff integration bounds for v0={v0}")

    # Extract parameters
    h, Sdi, Sil = params["h"], params["Sdi"], params["Sil"]
    fc, Sm, ts = params["fc"], params["Sm"], params["ts"]

    # Calculate integration bounds
    Sd = h * Sdi + (1 - h) * Sil
    Sdd = Sil - Sdi
    t234 = (v0 / h - Sdi) / (fc * (1 - h))

    threshold1 = h * Sdd
    threshold2 = h * (Sdd + Sm)
    logger.debug(f"Thresholds: threshold1={threshold1}, threshold2={threshold2}")

    zeros = lambda t: np.zeros_like(np.asarray(t, dtype=float))

    if 0 <= v0 <= threshold1:
        logger.debug("Condition met: 0 <= v0 <= threshold1")
        return [
            {
                "a": lambda t: zeros(t),
                "b": lambda t: np.full_like(np.asarray(t, dtype=float), v0_limit),
                "c": lambda t: zeros(t),
                "d": lambda t: np.full_like(np.asarray(t, dtype=float), v0 / h + Sdi),
            }
        ]

    if threshold1 < v0 <= threshold2:
        logger.debug("Condition met: threshold1 < v0 <= threshold2")
        return [
            {
                "a": lambda t: zeros(t),
                "b": lambda t: np.full_like(np.asarray(t, dtype=float), t234),
                "c": lambda t: zeros(t),
                "d": lambda t: Sd + v0 + fc * (1 - h) * np.asarray(t, dtype=float),
            },
            {
                "a": lambda t: np.full_like(np.asarray(t, dtype=float), t234),
                "b": lambda t: np.full_like(np.asarray(t, dtype=float), v0_limit),
                "c": lambda t: zeros(t),
                "d": lambda t: np.full_like(np.asarray(t, dtype=float), v0 / h + Sdi),
            },
        ]

    if v0 > threshold2:
        logger.debug("Condition met: v0 > threshold2")
        return [
            {
                "a": lambda t: zeros(t),
                "b": lambda t: np.full_like(np.asarray(t, dtype=float), ts),
                "c": lambda t: zeros(t),
                "d": lambda t: Sd + v0 + fc * (1 - h) * np.asarray(t, dtype=float),
            },
            {
                "a": lambda t: np.full_like(np.asarray(t, dtype=float), ts),
                "b": lambda t: np.full_like(np.asarray(t, dtype=float), v0_limit),
                "c": lambda t: zeros(t),
                "d": lambda t: np.full_like(np.asarray(t, dtype=float), Sd + v0 + (1 - h) * Sm),
            },
        ]

    logger.warning(f"No integration bounds determined for v0={v0}")
    return []