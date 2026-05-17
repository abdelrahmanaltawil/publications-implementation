"""Validation utilities for comparing optimization vs. simulation results.

Used by test_algorithm_tasks.py to run end-to-end scenarios, extract
time series from both the Pyomo model and WNTR/EPANET simulation, and
assert they agree within tolerance.
"""

import contextlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyomo.environ as pyo
import wntr

from src.algorithm_tasks import build_model, solve_model
from src.helpers.energy.energy_simulation import run_energy_simulation
from src.helpers.water.water_simulation import load_water_network, run_water_simulation
from src.preprocessing import _build_energy_data

logger = logging.getLogger("econex.tests.validation")


# ---------------------------------------------------------------------------
# Logging context manager
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def validation_logging(report_file: Path):
    """Route validation logs to a dedicated file for the duration of a test."""
    log = logging.getLogger("econex.tests.validation")
    for h in log.handlers[:]:
        log.removeHandler(h)

    fhandler = logging.FileHandler(report_file, mode="w")
    fhandler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    log.addHandler(fhandler)
    log.setLevel(logging.DEBUG)
    log.info(f"Test Report — {report_file.parent.name}")
    log.info("=" * 60)
    try:
        yield log
    finally:
        log.info("=" * 60)
        log.info("End of Report")
        fhandler.close()
        log.removeHandler(fhandler)


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def compare_series(
    opt_series: Union[pd.Series, np.ndarray, float],
    sim_series: Union[pd.Series, np.ndarray, float],
) -> Dict:
    """Compute comparison metrics between an optimization and simulation series.

    Returns:
        Dict with n, mae, max_diff, max_rel_err_pct, mean_rel_err_pct,
        correlation, and internal arrays prefixed with '_'.
    """
    opt_arr = np.atleast_1d(opt_series).astype(float)
    sim_arr = np.atleast_1d(sim_series).astype(float)
    min_len = min(len(opt_arr), len(sim_arr))
    opt_arr, sim_arr = opt_arr[:min_len], sim_arr[:min_len]

    abs_diff = np.abs(opt_arr - sim_arr)
    with np.errstate(divide="ignore", invalid="ignore"):
        rel_err = abs_diff / np.abs(sim_arr)
        rel_err[np.abs(sim_arr) < 1e-6] = np.nan

    corr = (float(np.corrcoef(opt_arr, sim_arr)[0, 1])
            if np.std(opt_arr) > 1e-9 and np.std(sim_arr) > 1e-9
            else (1.0 if np.allclose(opt_arr, sim_arr) else 0.0))

    return {
        "n": len(opt_arr),
        "mae": float(np.mean(abs_diff)),
        "max_diff": float(np.max(abs_diff)),
        "max_rel_err_pct": float(np.nanmax(rel_err) * 100) if not np.all(np.isnan(rel_err)) else 0.0,
        "mean_rel_err_pct": float(np.nanmean(rel_err) * 100) if not np.all(np.isnan(rel_err)) else 0.0,
        "correlation": corr,
    }






# Time series extraction
# ---------------------------------------------------------------------------

def extract_water_opt_timeseries(model: pyo.ConcreteModel,
                                    wn: wntr.network.WaterNetworkModel) -> Dict:
    """Extract head and flow time series from a solved Pyomo model."""
    time_steps = list(model.T)
    dt = pyo.value(model.dt)
    time_index = [t * dt for t in time_steps]

    def extract_var(names, var, attr="T"):
        out = {}
        for name in names:
            if name in getattr(model, attr if attr != "T" else "Nodes", []) or True:
                try:
                    out[name] = [pyo.value(var[name, t]) for t in time_steps]
                except Exception:
                    pass
        return pd.DataFrame(out, index=time_index)

    return {
        "tank_heads":    extract_var(wn.tank_name_list, model.H),
        "junction_heads": extract_var(wn.junction_name_list, model.H),
        "pump_flows":    extract_var(wn.pump_name_list, model.Q),
        "pipe_flows":    extract_var(wn.pipe_name_list, model.Q),
    }


def extract_water_sim_timeseries(wn: wntr.network.WaterNetworkModel,
                                   sim_results, num_steps: int) -> Dict:
    """Extract head and flow time series from WNTR simulation results."""
    timestep = wn.options.time.report_timestep
    time_index = list(range(0, num_steps * timestep, timestep))[:num_steps]

    def safe_extract(df, name):
        try:
            return df[name].loc[time_index].values
        except Exception:
            return df[name].values[:num_steps]

    return {
        "tank_heads":    pd.DataFrame({t: safe_extract(sim_results.node["head"], t) for t in wn.tank_name_list}, index=time_index),
        "junction_heads": pd.DataFrame({t: safe_extract(sim_results.node["head"], t) for t in wn.junction_name_list}, index=time_index),
        "pump_flows":    pd.DataFrame({t: safe_extract(sim_results.link["flowrate"], t) for t in wn.pump_name_list}, index=time_index),
        "pipe_flows":    pd.DataFrame({t: safe_extract(sim_results.link["flowrate"], t) for t in wn.pipe_name_list}, index=time_index),
    }


def compute_comparison_metrics(opt_data: Dict, sim_data: Dict) -> Dict:
    """Compute MAE, max error, and correlation for each component and data type."""
    metrics = {}
    dtypes = set(opt_data.keys()) | set(sim_data.keys())
    for dtype in dtypes:
        opt_df = opt_data.get(dtype, pd.DataFrame())
        sim_df = sim_data.get(dtype, pd.DataFrame())
        if opt_df.empty or sim_df.empty:
            continue
        common = set(opt_df.columns) & set(sim_df.columns)
        if not common:
            continue
        metrics[dtype] = {
            col: {k: round(v, 6) for k, v in compare_series(
                opt_df[col].values, sim_df[col].values[:len(opt_df)]
            ).items()}
            for col in common
        }
    return metrics


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_validation_results(opt_data: Dict, sim_data: Dict, save_dir: Path) -> None:
    """Generate and save overlay plots for Pyomo vs. Simulation time series."""
    save_dir.mkdir(parents=True, exist_ok=True)
    
    dtypes = set(opt_data.keys()) | set(sim_data.keys())
    for dtype in dtypes:
        opt_df = opt_data.get(dtype, pd.DataFrame())
        sim_df = sim_data.get(dtype, pd.DataFrame())
        
        if opt_df.empty or sim_df.empty:
            continue
            
        common = sorted(list(set(opt_df.columns) & set(sim_df.columns)))
        if not common:
            continue
            
        dtype_dir = save_dir / dtype
        dtype_dir.mkdir(exist_ok=True)
        
        logger.info(f"Plotting {len(common)} items for {dtype}...")
        
        plot_items = common
        chunk_size = 12
        
        for i in range(0, len(plot_items), chunk_size):
            chunk = plot_items[i:i + chunk_size]
            n_items = len(chunk)
            
            cols = min(4, n_items)
            rows = (n_items + cols - 1) // cols
            
            fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4 * rows))
            if n_items == 1:
                axes = np.array([axes])
            axes = axes.flatten()
            
            for idx, col in enumerate(chunk):
                ax = axes[idx]
                opt_series = opt_df[col].values
                sim_series = sim_df[col].values[:len(opt_series)]
                t_hours = np.arange(len(opt_series))
                
                ax.plot(t_hours, sim_series, label='EPANET Simulation', linestyle='--', marker='o', alpha=0.7)
                ax.plot(t_hours, opt_series, label='Pyomo Optimization', linestyle='-', alpha=0.7)
                
                ax.set_title(f"{dtype.replace('_', ' ').title()} - {col}")
                ax.set_xlabel("Time Step (Hour)")
                ax.set_ylabel("Value")
                ax.legend()
                ax.grid(True, alpha=0.3)
                
            for idx in range(n_items, len(axes)):
                axes[idx].set_visible(False)
                
            plt.tight_layout()
            part_suffix = f"_part_{i // chunk_size + 1}" if len(plot_items) > chunk_size else ""
            plt.savefig(dtype_dir / f"plot{part_suffix}.png", dpi=150)
            plt.close()


def extract_energy_opt_timeseries(model: pyo.ConcreteModel, buses: list, lines: list) -> Dict:
    """Extract voltage, power, and current time series from a solved Pyomo model."""
    time_steps = list(model.T)
    dt = pyo.value(model.dt)
    time_index = [t * dt for t in time_steps]

    def extract_var(names, var):
        out = {}
        for name in names:
            if name in getattr(model, var.name.split('[')[0], getattr(model, "Buses", [])):
                try:
                    out[name] = [pyo.value(var[name, t]) for t in time_steps]
                except Exception:
                    pass
        return pd.DataFrame(out, index=time_index)
        
    line_names = list(model.ELines) if hasattr(model, "ELines") else []
    
    # Calculate net power injection: import - export
    P_injections = {}
    Q_injections = {} # Q is not modeled as injection variable directly, maybe just 0
    for b in buses:
        if hasattr(model, "Buses") and b in model.Buses:
            try:
                P_inj = [pyo.value(model.P_import[b,t]) - pyo.value(model.P_export[b,t]) for t in time_steps]
                P_injections[b] = P_inj
            except:
                pass

    return {
        "voltage_pu": extract_var(buses, getattr(model, "U", None)) if hasattr(model, "U") else pd.DataFrame(),
        "P_kw": pd.DataFrame(P_injections, index=time_index),
        # Current mag approx: sqrt(phi^2 + chi^2), maybe later if needed
    }


def run_energy_validation(
    dss_file: str,
    num_timesteps: int = 24,
    solver: str = "gurobi",
    save_dir: Path = None,
) -> dict:
    """Build, solve, simulate, and compare results for an energy network scenario."""
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Energy Scenario: {Path(dss_file).name} | T={num_timesteps} | solver={solver}")

    # Build and solve
    config = {"run_water": False, "run_energy": True, "run_nexus": False, "T": num_timesteps}
    
    # We must construct a valid energy_cfg to pass to build_model. 
    # Since preprocessing uses a placeholder, the models might not align! 
    # But we run it anyway to test the flow.
    energy_cfg = {"network": dss_file, "technologies": {}, "cost": {}}
    energy_data = _build_energy_data(energy_cfg, Path(dss_file), num_timesteps)
    data = {"energy": energy_data}

    model = build_model(data, config)
    if hasattr(model, "objective"):
        model.del_component(model.objective)
    model.objective = pyo.Objective(expr=0, sense=pyo.minimize)

    model, results = solve_model(model, solver=solver, tee=False)
    term = results.solver.termination_condition
    logger.info(f"Solver termination: {term}")

    if term != pyo.TerminationCondition.optimal:
        return {"status": "infeasible", "termination": str(term)}

    # Simulate
    sim_results = run_energy_simulation(dss_file, mode="daily")
    
    # Map simulation index from hour steps to seconds to match optimization dt
    dt = 3600
    sim_time_index = [t * dt for t in range(num_timesteps)]
    
    sim_data = {
        "voltage_pu": pd.DataFrame(sim_results["node"]["voltage_pu"]).set_index(pd.Index(sim_time_index)),
        "P_kw": pd.DataFrame(sim_results["node"]["P_kw"]).set_index(pd.Index(sim_time_index)),
        "Q_kvar": pd.DataFrame(sim_results["node"]["Q_kvar"]).set_index(pd.Index(sim_time_index)),
        "current_amps": pd.DataFrame(sim_results["link"]["current_amps"]).set_index(pd.Index(sim_time_index)),
    }

    opt_data = extract_energy_opt_timeseries(model, energy_data["buses"], energy_data["lines"])
    metrics = compute_comparison_metrics(opt_data, sim_data)

    if save_dir:
        with open(save_dir / "comparison_metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
            
        plot_validation_results(opt_data, sim_data, save_dir)

    return {
        "status": "completed",
        "metrics": metrics,
        "opt_data": opt_data,
        "sim_data": sim_data,
    }

# ---------------------------------------------------------------------------
# End-to-end scenario runner
# ---------------------------------------------------------------------------

def run_water_validation(
    inp_file: str,
    num_timesteps: int = 24,
    solver: str = "gurobi",
    save_dir: Path = None,
) -> dict:
    """Build, solve, simulate, and compare results for a water network scenario.

    Builds the water-only optimization model, solves with a zero objective
    (feasibility check), runs EPANET simulation, and returns comparison metrics.

    Args:
        inp_file:       Path to EPANET .inp file.
        num_timesteps:  Number of hourly time steps (default 24).
        solver:         MILP solver name.
        save_dir:       Optional directory to save metrics JSON and plots.

    Returns:
        Dict with 'status', 'metrics', 'opt_data', 'sim_data'.
    """
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Scenario: {Path(inp_file).name} | T={num_timesteps} | solver={solver}")

    # --- Step 1: Run EPANET simulation ---
    wn = load_water_network(inp_file)
    wn.options.time.duration = num_timesteps * 3600
    wn.options.time.hydraulic_timestep = 3600
    wn.options.time.report_timestep = 3600
    # Do NOT override pattern_timestep — must stay at the .inp file's original value.
    sim_results = run_water_simulation(wn, simulator_type="epanet")

    # Extract per-pipe and per-pump per-timestep flows for linearized head loss.
    # MILPNet approach: use simulation operating points to linearize H-W and pump
    # curves, eliminating all binary SOS2 variables → pure LP, solves in seconds.
    flowrate_df = sim_results.link["flowrate"]
    pipe_flows_sim = {}
    pump_flows_sim = {}
    for pipe in wn.pipe_name_list:
        if pipe in flowrate_df.columns:
            pipe_flows_sim[pipe] = [float(flowrate_df[pipe].iloc[t]) for t in range(num_timesteps)]
    for pump in wn.pump_name_list:
        if pump in flowrate_df.columns:
            pump_flows_sim[pump] = [float(flowrate_df[pump].iloc[t]) for t in range(num_timesteps)]

    # --- Step 2: Build and solve the optimizer ---
    data = {
        "water": {
            "inp_file": inp_file,
            "config": {"T": num_timesteps},
            "pipe_flows_sim": pipe_flows_sim,
            "pump_flows_sim": pump_flows_sim,
        }
    }
    config = {"run_water": True, "run_energy": False, "run_nexus": False, "T": num_timesteps}

    model = build_model(data, config)

    # Fix pump and valve status to match EPANET's initial schedule.
    # Without this the solver turns all pumps off (Status=0), producing zero
    # flow everywhere while EPANET runs them — causing 100% error.
    for p in model.Pumps:
        is_on = str(wn.get_link(p).initial_status).upper() not in ("CLOSED",)
        for t in model.T:
            model.Status[p, t].fix(1 if is_on else 0)
    for v in model.Valves:
        is_on = str(wn.get_link(v).initial_status).upper() not in ("CLOSED",)
        for t in model.T:
            model.Status[v, t].fix(1 if is_on else 0)

    model.del_component(model.objective)
    # Minimise demand-violation slack so the solver finds the physics-consistent solution
    model.objective = pyo.Objective(
        expr=sum(
            model.SlackPos[n, t] + model.SlackNeg[n, t]
            for n in model.Junctions for t in model.T
        ),
        sense=pyo.minimize,
    )

    model, results = solve_model(model, solver=solver, tee=False, timeout=120)
    term = results.solver.termination_condition
    logger.info(f"Solver termination: {term}")

    # Accept optimal, feasible, or time-limit-with-incumbent.
    # Gurobi loads the best incumbent into the model even on time limit (the Pyomo warning
    # "containing a solution" confirms this). Infeasible/unbounded/error are rejected.
    _acceptable = {
        pyo.TerminationCondition.optimal,
        pyo.TerminationCondition.feasible,
        pyo.TerminationCondition.maxTimeLimit,
    }
    if term not in _acceptable:
        return {"status": "infeasible", "termination": str(term)}

    # --- Step 3: Extract and compare ---
    opt_data = extract_water_opt_timeseries(model, wn)
    sim_data = extract_water_sim_timeseries(wn, sim_results, num_timesteps)
    metrics = compute_comparison_metrics(opt_data, sim_data)

    if save_dir:
        with open(save_dir / "comparison_metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
        plot_validation_results(opt_data, sim_data, save_dir)

    return {
        "status": "completed",
        "metrics": metrics,
        "opt_data": opt_data,
        "sim_data": sim_data,
        "timestep": wn.options.time.report_timestep,
    }
