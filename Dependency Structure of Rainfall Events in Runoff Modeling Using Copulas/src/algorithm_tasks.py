# imports
import logging
import joblib
import os
import warnings
import numpy as np
import pandas as pd
import scipy.stats as stats
from scipy.integrate import IntegrationWarning


# local imports
import helpers.utils


def fit_copulas(data: pd.DataFrame, corr_columns: list, copula_families: list) -> tuple:
    """Fits multiple copula families to the data and computes fit metrics."""

    logging.info("Starting copula fitting process...")

    # Extract volume and duration
    volume = data[corr_columns[0]]
    duration = data[corr_columns[1]]

    logging.info(f"Data points for fitting: {len(volume)}")

    # Prepare data for copula fitting
    uv = np.column_stack(
        (
            stats.rankdata(duration, method="average") / (len(duration) + 1),
            stats.rankdata(volume, method="average") / (len(volume) + 1),
        )
    )
    uv_df = pd.DataFrame(uv, columns=["u_duration", "v_volume"])


    # Get copula constructors
    copulas = helpers.utils.get_copula_families(copula_families)

    fitted_copulas = {}
    metrics = []
    n = len(uv)

    for name, function in copulas.items():
        logging.info(f"Fitting copula family: {name}")
        
        # Fit copula
        param = function().fit_corr_param(uv)
        copula = function(param)
        fitted_copulas[name] = copula

        # Compute metrics
        loglik = float(np.sum(np.log(copula.pdf(uv) + 1e-15)))
        k_params = 2 if name == "t" else 1
        aic = 2 * k_params - 2 * loglik
        bic = k_params * np.log(n) - 2 * loglik
        taildep = copula.dependence_tail() if hasattr(copula, "dependence_tail") else (np.nan, np.nan)

        metrics.append(
            {
                "Family": name,
                "param": float(param),
                "df": getattr(copula, "df", np.nan),
                "LogLik": loglik,
                "AIC": aic,
                "BIC": bic,
                "taildep.lower": float(taildep[0]) if taildep[0] is not np.nan else np.nan,
                "taildep.upper": float(taildep[1]) if taildep[1] is not np.nan else np.nan,
                "tau": float(copula.tau()),
            }
        )
    metrics_df = pd.DataFrame(metrics)

    logging.info("Copula fitting completed.")
    return uv_df, fitted_copulas, metrics_df 


def get_copula_joint_density_function(copulas: dict, lambda_v: float, lambda_t: float) -> dict:
    """Builds the joint density function for runoff volume and duration based on the fitted copula."""

    logging.info("Building joint density functions for runoff volume and duration...")
    logging.info(f"Using lambda_v={lambda_v:.4f}, lambda_t={lambda_t:.4f}")
    joint_densities = {}

    def _create_density(copula_instance):
        def joint_density(v, t):
            '''Joint density function f(v, t) using the copula and marginal exponentials.'''
            
            # Ensure inputs are numpy arrays
            v = np.asarray(v, dtype=float)
            t = np.asarray(t, dtype=float)

            # Marginal CDFs and PDFs of exponential distributions
            F_V = lambda v : stats.expon.cdf(v, scale=1 / lambda_v)
            F_T = lambda t : stats.expon.cdf(t, scale=1 / lambda_t)
            f_V = lambda v : stats.expon.pdf(v, scale=1 / lambda_v)
            f_T = lambda t : stats.expon.pdf(t, scale=1 / lambda_t)

            # Compute joint density using copula PDF and marginal PDFs
            uv = np.column_stack((F_V(v), F_T(t)))
            return copula_instance.pdf(uv) * f_V(v) * f_T(t)
        return joint_density

    for name, copula in copulas.items():
        joint_densities[name] = _create_density(copula)

    return joint_densities


def compute_cdf(
        joint_densities: dict, 
        physical_params: dict, 
        analysis_params: dict, 
        integration_method: str, **kwargs
        ) -> pd.DataFrame:

    logging.info(f"Starting CDF computation using method: {integration_method}")

    # Prepare v0 values
    num_points = int(analysis_params["v0_range_max"])
    v0_vals = np.linspace(0, analysis_params["v0_range_max"], num=num_points)

    # Determine number of parallel jobs
    N_JOBS = max(os.cpu_count() - 1, 1)
    logging.info(f"Parallel execution with {N_JOBS} jobs.")
    
    # Get integration scheme
    integration_scheme = helpers.utils.get_integration_scheme(integration_method, **kwargs)

    # Pre-calculate integration bounds for all v0 points
    logging.info("Pre-calculating integration bounds...")
    v0_bounds_list = [
        helpers.utils.get_runoff_integration_bounds(
            v0, 
            physical_params, 
            v0_limit=analysis_params["v0_limit"]
        )
        for v0 in v0_vals
    ]

    # Flatten tasks: (joint_density, bounds)
    tasks = []
    copula_names = list(joint_densities.keys())
    for name in copula_names:
        density = joint_densities[name]
        for bounds in v0_bounds_list:
            tasks.append((density, bounds))

    logging.info(f"Total tasks: {len(tasks)}")

    def _worker(joint_density, bounds, scheme):
        subtotal = 0.0
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=IntegrationWarning)
            for bnd in bounds:
                subtotal += scheme(
                    joint_density,
                    a=float(bnd["a"](0)),
                    b=float(bnd["b"](0)),
                    c=bnd["c"],
                    d=bnd["d"],
                )
        return subtotal

    # Compute CDF values in parallel
    results = joblib.Parallel(n_jobs=N_JOBS, verbose=0)(
        joblib.delayed(_worker)(density, bounds, integration_scheme) for density, bounds in tasks
    )

    # Reconstruct results
    cdf_results = {}
    n_points = len(v0_vals)
    for i, name in enumerate(copula_names):
        start_idx = i * n_points
        end_idx = start_idx + n_points
        cdf_results[name] = np.array(results[start_idx:end_idx])

    cdf_results = pd.DataFrame(cdf_results)
    cdf_results.insert(0, "v0", v0_vals)
    logging.info("CDF computation completed.")
    return cdf_results


def runoff_volume_cdf_closed_form(physical_params: dict, analysis_params: dict) -> np.ndarray:
    '''Computes the closed-form CDF of runoff volume v0 based on physical model parameters and exponential rates.'''
    logging.info("Computing closed-form analytical CDF...")

    # Prepare v0 values
    v0_vals = np.linspace(0, analysis_params["v0_range_max"], num=analysis_params["v0_range_max"])

    # Extract parameters
    h = physical_params["h"]
    Sdi = physical_params["Sdi"]
    Sil = physical_params["Sil"]
    fc = physical_params["fc"]
    Sm = physical_params["Sm"]
    ts = physical_params["ts"]
    lambda_v = physical_params["lambda_v"]
    lambda_t = physical_params["lambda_t"]

    # Compute CDF
    v0 = np.asarray(v0_vals, dtype=float)
    Sd = h * Sdi + (1 - h) * Sil
    Sdd = Sil - Sdi
    C_param = lambda_t / (lambda_t + lambda_v * fc * (1 - h))

    threshold1 = h * Sdd
    threshold2 = h * (Sdd + Sm)

    cdf = np.zeros_like(v0)

    # Compute CDF for the first threshold
    idx1 = (0 <= v0) & (v0 <= threshold1)
    cdf[idx1] = 1 - np.exp(-lambda_v * Sdi - lambda_v * v0[idx1] / h)

    # Compute CDF for the second threshold
    idx2 = (v0 > threshold1) & (v0 <= threshold2)
    v_part = v0[idx2]
    term1 = (1 - C_param) * np.exp(-lambda_v * Sdi - lambda_v * v_part / h - lambda_t * (v_part - h * Sdd) / (h * fc))
    term2 = C_param * np.exp(-lambda_v * Sd - lambda_v * v_part)
    cdf[idx2] = 1 - term1 - term2

    # Compute CDF for values above the second threshold
    idx3 = v0 > threshold2
    v_part = v0[idx3]
    term1 = (1 - C_param) * np.exp(-lambda_v * Sd - lambda_v * v_part - lambda_v * (1 - h) * Sm - lambda_t * ts)
    term2 = C_param * np.exp(-lambda_v * Sd - lambda_v * v_part)
    cdf[idx3] = 1 - term1 - term2

    return cdf


def compute_return_period(cdf_results: pd.DataFrame, analysis_params: dict) -> pd.DataFrame:
    '''Return Period Analysis'''

    # Extract v0 values if present, otherwise regenerate
    v0_vals = cdf_results["v0"].to_numpy()
    cdf_data = cdf_results.drop(columns=["v0"])

    # Return period analysis
    return_periods = np.array(analysis_params["return_periods"], dtype=float)
    target_cdf = 1 - 1 / (analysis_params["events_per_year"] * return_periods)

    v0_for_return = {}
    for name in cdf_data.columns:
        cdf_vals = cdf_data[name].to_numpy()
        v0_quantiles = np.interp(target_cdf, cdf_vals, v0_vals)
        v0_for_return[name] = v0_quantiles

    return_periods_results = pd.DataFrame({"ReturnPeriod": return_periods, **v0_for_return})

    return return_periods_results


def perform_bootstrap_uncertainty_analysis(
    data: pd.DataFrame,
    corr_columns: list,
    copula_families: list,
    physical_params: dict,
    analysis_params: dict,
    integration_method: str,
    integration_kwargs: dict,
    n_bootstrap: int = 50
) -> dict:
    """
    Performs bootstrap resampling to estimate uncertainty in copula parameters and return levels.
    """
    logging.info(f"Starting bootstrap analysis with {n_bootstrap} iterations.")
    
    # Storage
    bootstrap_params = {family: [] for family in copula_families}
    bootstrap_return_levels = {family: [] for family in copula_families}
    bootstrap_data = []
    
    # Get copula constructors
    copulas = helpers.utils.get_copula_families(copula_families)
    
    # Suppress logging for inner loop to avoid spam
    logger = logging.getLogger()
    prev_level = logger.level
    
    for i in range(n_bootstrap):
        if (i + 1) % 5 == 0:
            logging.info(f"Bootstrap iteration {i + 1}/{n_bootstrap}")

        # 1. Resample data
        sample = data.sample(n=len(data), replace=True)
        vol = sample[corr_columns[0]].values
        dur = sample[corr_columns[1]].values
        
        # 2. Re-estimate marginal parameters
        lambda_v_sample = 1.0 / np.mean(vol)
        lambda_t_sample = 1.0 / np.mean(dur)
        
        # 3. Fit Copulas
        uv_sample = np.column_stack(
            (
                stats.rankdata(dur, method="average") / (len(dur) + 1),
                stats.rankdata(vol, method="average") / (len(vol) + 1),
            )
        )
        
        fitted_copulas_sample = {}
        for name, function in copulas.items():
            try:
                # Fit parameter
                param = function().fit_corr_param(uv_sample)
                bootstrap_params[name].append(float(param))
                fitted_copulas_sample[name] = function(param)
            except Exception as e:
                bootstrap_params[name].append(np.nan)

        # 4. Compute Joint Densities & CDFs & Return Periods
        # Suppress logging for inner loop operations to avoid spamming "Building joint density..."
        logger.setLevel(logging.WARNING)
        rp_df = None
        try:
            joint_densities_sample = get_copula_joint_density_function(
                fitted_copulas_sample, lambda_v_sample, lambda_t_sample
            )

            if joint_densities_sample:
                cdf_df = compute_cdf(
                    joint_densities=joint_densities_sample,
                    physical_params=physical_params,
                    analysis_params=analysis_params,
                    integration_method=integration_method,
                    **integration_kwargs
                )
                
                # Compute Return Periods
                rp_df = compute_return_period(cdf_df, analysis_params)
                
                for name in rp_df.columns:
                    if name != "ReturnPeriod":
                        bootstrap_return_levels[name].append(rp_df[name].values)
        finally:
            logger.setLevel(prev_level)

        # Record detailed results for this iteration
        for name in copula_families:
            param_val = bootstrap_params[name][-1] if bootstrap_params[name] else np.nan
            row = {
                "iteration": i + 1,
                "copula_type": name,
                "parameter": param_val
            }
            
            if rp_df is not None and name in rp_df.columns:
                for _, r_row in rp_df.iterrows():
                    row[f"RP_{int(r_row['ReturnPeriod'])}"] = r_row[name]
            else:
                for rp in analysis_params["return_periods"]:
                    row[f"RP_{int(rp)}"] = np.nan
            
            bootstrap_data.append(row)

    # Aggregate results
    results = {
        "parameters": {},
        "return_levels": {}
    }
    
    for name in copula_families:
        # Parameters
        params = np.array(bootstrap_params[name])
        results["parameters"][name] = {
            "mean": np.nanmean(params),
            "std": np.nanstd(params),
            "CI_95": np.nanpercentile(params, [2.5, 97.5]) if len(params) > 0 else [np.nan, np.nan]
        }
        
        # Return Levels
        rls = np.array(bootstrap_return_levels[name]) # Shape: (n_boot, n_return_periods)
        if rls.size > 0:
            results["return_levels"][name] = {
                "mean": np.nanmean(rls, axis=0),
                "std": np.nanstd(rls, axis=0),
                "CI_95_lower": np.nanpercentile(rls, 2.5, axis=0),
                "CI_95_upper": np.nanpercentile(rls, 97.5, axis=0)
            }
            
    # Create DataFrame
    bootstrap_data = pd.DataFrame(bootstrap_data)

    logging.info("Bootstrap analysis completed.")
    return bootstrap_data


def perform_sensitivity_analysis(
    copula_families: list,
    parameter_range: dict,
    physical_params: dict,
    analysis_params: dict,
    integration_method: str,
    integration_kwargs: dict
) -> pd.DataFrame:
    """
    Performs sensitivity analysis by varying the copula parameter.
    """
    logging.info(f"Running sensitivity analysis for {copula_families}...")
    
    # Suppress logging for inner loop operations to avoid spamming "Building joint density..."
    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)

    # Get copula constructors
    copulas = helpers.utils.get_copula_families(copula_families)
    
    copulas_dict = {}
    for name, function in copulas.items():
        for param in parameter_range[name]:
            cop_instance = function(param)
            study_name = f"{name}_param_{param:.2f}"
            copulas_dict[study_name] = cop_instance

    joint_densities = get_copula_joint_density_function(copulas_dict, physical_params["lambda_v"], physical_params["lambda_t"])
        
    # Compute CDFs
    cdf_df = compute_cdf(
        joint_densities=joint_densities,
        physical_params=physical_params,
        analysis_params=analysis_params,
        integration_method=integration_method,
        **integration_kwargs
    )

    # Compute Return Periods
    rp_df = compute_return_period(cdf_df, analysis_params)
    
    logger.setLevel(logging.INFO)
    logging.info("Sensitivity analysis completed.")

    return rp_df