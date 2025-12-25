# Algorithm Module

> **Source**: [`src/algorithm_tasks.py`](../../../src/algorithm_tasks.py)  
> **Last Updated**: 2024-12-24

## Overview

The algorithm module implements the core copula-based probabilistic model for rainfall-runoff analysis. It provides copula fitting, CDF computation, return period calculation, and sensitivity/uncertainty analysis.

---

## Core Functions

### `fit_copulas(data, corr_columns, copula_families)`

Fits multiple copula families to bivariate rainfall data and computes fit metrics.

| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | `pd.DataFrame` | Rainfall events data |
| `corr_columns` | `list` | Columns to model (e.g., `["Volume (mm)", "Duration (hrs)"]`) |
| `copula_families` | `list` | Families to fit (e.g., `["Gaussian", "Clayton"]`) |

**Returns**: Tuple of:
1. `pd.DataFrame` - Pseudo-observations (ranks)
2. `dict` - Fitted copula instances
3. `pd.DataFrame` - Fit metrics

**Fit Metrics Computed**:
| Metric | Description |
|--------|-------------|
| `AIC` | Akaike Information Criterion |
| `BIC` | Bayesian Information Criterion |
| `Log-Likelihood` | Model log-likelihood |
| `Kendall's τ` | Rank correlation |
| `Lower Tail Dep.` | Lower tail dependence coefficient |
| `Upper Tail Dep.` | Upper tail dependence coefficient |

**Supported Copula Families**:
| Family | Parameter | Tail Dependence |
|--------|-----------|-----------------|
| Gaussian | ρ (correlation) | None |
| t (Student) | ρ, df | Symmetric |
| Clayton | θ > 0 | Lower only |
| Gumbel | θ ≥ 1 | Upper only |
| Frank | θ ≠ 0 | None |

---

### `get_copula_joint_density_function(copulas, lambda_v, lambda_t)`

Constructs joint density functions combining the copula with exponential marginals.

| Parameter | Type | Description |
|-----------|------|-------------|
| `copulas` | `dict` | Fitted copula instances |
| `lambda_v` | `float` | Exponential rate for volume (1/mean) |
| `lambda_t` | `float` | Exponential rate for duration (1/mean) |

**Returns**: `dict` - Joint density functions for each copula

**Mathematical Form**:
```
f(v,t) = c(F_V(v), F_T(t)) × f_V(v) × f_T(t)
```
where:
- `c(u,v)` is the copula density
- `F_V, F_T` are exponential CDFs
- `f_V, f_T` are exponential PDFs

---

### `compute_cdf(joint_densities, physical_params, analysis_params, integration_method, **kwargs)`

Computes the CDF of runoff volume by integrating over the joint density.

| Parameter | Type | Description |
|-----------|------|-------------|
| `joint_densities` | `dict` | Joint density functions |
| `physical_params` | `dict` | Catchment parameters |
| `analysis_params` | `dict` | Analysis settings |
| `integration_method` | `str` | `"ADAPTIVE_2D_QUADRATURE"` or `"MONTE_CARLO"` |

**Physical Parameters Required**:
| Key | Symbol | Description | Units |
|-----|--------|-------------|-------|
| `h` | h | Imperviousness fraction | - |
| `Sdi` | S_di | Impervious depression storage | mm |
| `Sil` | S_il | Pervious initial loss | mm |
| `fc` | f_c | Ultimate infiltration rate | mm/hr |
| `Sm` | S_m | Maximum infiltration storage | mm |
| `ts` | t_s | Time to saturation | hr |

**Returns**: `pd.DataFrame` with columns `v0` and CDF values for each copula.

---

### `runoff_volume_cdf_closed_form(physical_params, analysis_params)`

Computes the analytical closed-form CDF (assumes independence).

| Parameter | Type | Description |
|-----------|------|-------------|
| `physical_params` | `dict` | Catchment parameters + `lambda_v`, `lambda_t` |
| `analysis_params` | `dict` | Range settings |

**Returns**: `pd.Series` - Analytical CDF values

> [!NOTE]
> The closed-form solution assumes independence between volume and duration. Compare with copula results to assess the impact of dependence.

---

### `compute_return_period(cdf_results, analysis_params)`

Calculates return levels for specified return periods.

| Parameter | Type | Description |
|-----------|------|-------------|
| `cdf_results` | `pd.DataFrame` | CDF values from `compute_cdf` |
| `analysis_params` | `dict` | Contains `return_periods`, `events_per_year` |

**Returns**: `pd.DataFrame` - Return levels for each copula and return period

**Formula**:
```
P_annual = 1 - (1 - P_event)^θ
Return Level = CDF^(-1)(1 - 1/T)
```
where θ = average events per year, T = return period in years.

---

## Sensitivity & Uncertainty Functions

### `perform_bootstrap_uncertainty_analysis(...)`

Estimates parameter and return level uncertainty via bootstrap resampling.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `pd.DataFrame` | - | Original events data |
| `n_bootstrap` | `int` | `50` | Number of resamples |
| (others) | - | - | Same as `compute_cdf` |

**Returns**: `pd.DataFrame` with bootstrap statistics (mean, std, CI)

---

### `perform_sensitivity_analysis(...)`

Analyzes CDF sensitivity to copula parameter variations.

| Parameter | Type | Description |
|-----------|------|-------------|
| `parameter_range` | `dict` | Parameter values to test per family |
| (others) | - | Same as `compute_cdf` |

**Returns**: `pd.DataFrame` with CDFs at each parameter value

---

## Usage Example

```python
import algorithm_tasks as algorithm

# Fit copulas
ranks, copulas, metrics = algorithm.fit_copulas(
    data=events_data,
    corr_columns=["Volume (mm)", "Duration (hrs)"],
    copula_families=["Gaussian", "Clayton", "Gumbel"]
)

# Create joint densities
joint_densities = algorithm.get_copula_joint_density_function(
    copulas=copulas,
    lambda_v=1/events_data["Volume (mm)"].mean(),
    lambda_t=1/events_data["Duration (hrs)"].mean()
)

# Compute CDF
cdf_results = algorithm.compute_cdf(
    joint_densities=joint_densities,
    physical_params=config["physics_model"],
    analysis_params=config["analysis"],
    integration_method="ADAPTIVE_2D_QUADRATURE",
    epsabs=1e-5
)
```

---

## Tests

Test file: [`tests/test_algorithm_tasks.py`](../../../tests/test_algorithm_tasks.py)

| Test | Description |
|------|-------------|
| `test_compute_cdf_basic` | Basic CDF computation with mocks |
| `test_compute_cdf_multiple_bounds` | Multiple integration regions |
| `test_compute_cdf_empty_densities` | Empty input handling |

Run tests:
```bash
python -m unittest tests.test_algorithm_tasks -v
```
