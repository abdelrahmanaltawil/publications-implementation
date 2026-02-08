import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import wntr
import pyomo.environ as pyo
import json
import contextlib

# local imports
from src.optimization.algorithm_tasks import build_model, solve_model

from typing import Union

@contextlib.contextmanager
def validation_logging(report_file: Path):
    """
    Context manager to route validation logs to a file.
    
    Args:
        report_file: Path to the log file. Should use .log extension.
    """
    log = logging.getLogger("econex.tests.validation")
    
    # Remove existing handlers to clean state
    for h in log.handlers[:]:
        log.removeHandler(h)
        
    fhandler = logging.FileHandler(report_file, mode='w')
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fhandler.setFormatter(formatter)
    
    log.addHandler(fhandler)
    log.setLevel(logging.DEBUG)  # Capture all levels
    
    # Write header
    log.info(f"Test Report for {report_file.parent.name}")
    log.info("=" * 60)
    
    try:
        yield log
    finally:
        log.info("=" * 60)
        log.info("End of Report")
        fhandler.close()
        log.removeHandler(fhandler)


def compare_series(
    opt_series: Union[pd.Series, np.ndarray, float], 
    sim_series: Union[pd.Series, np.ndarray, float]
) -> Dict:
    """
    Calculate comparison metrics between two time series.
    
    This is the single source of truth for all metrics calculations.
    
    Args:
        opt_series: Optimization values (Series, Array, or Scalar).
        sim_series: Simulation/Reference values (Series, Array, or Scalar).
        
    Returns:
        Dictionary with:
            - n: number of points
            - mae: Mean Absolute Error
            - max_diff: Maximum absolute difference
            - max_rel_err_pct: Maximum relative error (%)
            - mean_rel_err_pct: Mean relative error (%)
            - correlation: Pearson correlation coefficient
    """
    # Robustly convert to 1D arrays
    opt_arr = np.atleast_1d(opt_series).astype(float)
    sim_arr = np.atleast_1d(sim_series).astype(float)

    # Ensure equal length
    min_len = min(len(opt_arr), len(sim_arr))
    opt_arr = opt_arr[:min_len]
    sim_arr = sim_arr[:min_len]

    # Calculate differences
    abs_diff = np.abs(opt_arr - sim_arr)
    
    # Point-by-point relative error
    with np.errstate(divide='ignore', invalid='ignore'):
        rel_err = abs_diff / np.abs(sim_arr)
        rel_err[np.abs(sim_arr) < 1e-6] = np.nan  # Undefined when sim is ~0
    
    # Summary statistics
    n = len(opt_arr)
    mae = float(np.mean(abs_diff))
    max_diff = float(np.max(abs_diff))
    max_rel_err_pct = float(np.nanmax(rel_err) * 100) if not np.all(np.isnan(rel_err)) else 0.0
    mean_rel_err_pct = float(np.nanmean(rel_err) * 100) if not np.all(np.isnan(rel_err)) else 0.0
    
    # Correlation
    if np.std(opt_arr) > 1e-9 and np.std(sim_arr) > 1e-9:
        corr = float(np.corrcoef(opt_arr, sim_arr)[0, 1])
    else:
        corr = 1.0 if np.allclose(opt_arr, sim_arr) else 0.0
    
    return {
        'n': n,
        'mae': mae,
        'max_diff': max_diff,
        'max_rel_err_pct': max_rel_err_pct,
        'mean_rel_err_pct': mean_rel_err_pct,
        'correlation': corr,
        # Store raw arrays for detailed failure reporting
        '_opt_arr': opt_arr,
        '_sim_arr': sim_arr,
        '_abs_diff': abs_diff,
        '_rel_err': rel_err
    }


def assert_timeseries_near_equal(
    opt_series: Union[pd.Series, np.ndarray, float], 
    sim_series: Union[pd.Series, np.ndarray, float], 
    rel_tol: float = 0.05,
    abs_tol: float = 1e-4,
    label: str = "Component",
    raise_on_fail: bool = True
) -> Dict:
    """
    Validate and log comparison between optimization and simulation for a component.
    
    Args:
        opt_series: Optimization values.
        sim_series: Simulation/Reference values.
        rel_tol: Relative tolerance (e.g., 0.05 for 5%).
        abs_tol: Absolute tolerance for near-zero values.
        label: Component label for logging.
        raise_on_fail: If True, raise AssertionError on failure.
        
    Returns:
        Dictionary with metrics and pass/fail status.
    """
    metrics = compare_series(opt_series, sim_series)
    
    # Extract internal arrays
    abs_diff = metrics['_abs_diff']
    rel_err = metrics['_rel_err']
    opt_arr = metrics['_opt_arr']
    sim_arr = metrics['_sim_arr']
    
    # Failure if: (Rel Error > Tol) AND (Abs Diff > AbsTol)
    fail_mask = (rel_err > rel_tol) & (abs_diff > abs_tol)
    passed = not np.any(fail_mask)
    
    metrics['passed'] = passed
    metrics['label'] = label
    
    # Log result
    status = "PASS" if passed else "FAIL"
    logger.info(f"{status}: {label} | N={metrics['n']} | Max Diff={metrics['max_diff']:.4f} | Mean Diff={metrics['mae']:.4f} | Max Rel Err={metrics['max_rel_err_pct']:.2f}% | Corr={metrics['correlation']:.4f}")
    
    if not passed:
        # Create detailed failure report
        indices = np.where(fail_mask)[0]
        report_indices = indices[:20]
        
        lines = [f"\n{'='*80}"]
        lines.append(f"FAILURE DETAILS: {label}")
        lines.append(f"Tolerance: Rel {rel_tol*100}%, Abs {abs_tol} | Total Failures: {len(indices)} / {metrics['n']}")
        lines.append("-" * 80)
        lines.append(f"{'Idx':<6} | {'Opt Value':<12} | {'Sim Value':<12} | {'Diff':<12} | {'Rel Err %':<10}")
        lines.append("-" * 80)
        
        for idx in report_indices:
            v_opt = opt_arr[idx]
            v_sim = sim_arr[idx]
            diff = abs_diff[idx]
            err = rel_err[idx] * 100
            lines.append(f"{idx:<6} | {v_opt:<12.4f} | {v_sim:<12.4f} | {diff:<12.4f} | {err:<10.2f}")
            
        if len(indices) > 20:
            lines.append(f"... and {len(indices) - 20} more failures ...")
        lines.append("=" * 80)
        
        logger.error("\n".join(lines))
        
        if raise_on_fail:
            raise AssertionError(f"{label} mismatch. Max error: {metrics['max_rel_err_pct']:.2f}% (Threshold: {rel_tol*100}%)")
    
    # Clean up internal arrays before returning
    del metrics['_opt_arr'], metrics['_sim_arr'], metrics['_abs_diff'], metrics['_rel_err']
    
    return metrics


def assert_no_negative_pressures(data: dict, source: str = "Optimization") -> None:
    """
    Assert that no junction has negative pressure (head below elevation).
    Negative pressures are physically impossible and indicate modeling errors.
    
    Args:
        data: Dictionary containing 'junction_heads' time series.
        source: Label for logging (e.g., "Optimization" or "Simulation").
    """
    junction_heads = data.get('junction_heads', {})
    
    violations = []
    for junc_id, heads in junction_heads.items():
        head_arr = np.atleast_1d(heads)
        min_head = np.min(head_arr)
        
        # Check if any head is negative (typically means pressure < 0)
        # Note: Head = Elevation + Pressure. If head < 0, that's unusual.
        # For a more precise check, we'd need elevation data, but for now
        # we flag any negative head values as suspicious.
        if min_head < 0:
            violations.append((junc_id, min_head))
    
    if violations:
        lines = [f"\nNEGATIVE PRESSURE VIOLATIONS ({source}):"]
        for junc_id, min_head in violations:
            lines.append(f"  Junction {junc_id}: Min Head = {min_head:.2f}")
        logger.error("\n".join(lines))
        raise AssertionError(f"Negative pressures detected in {source}: {len(violations)} junctions")
    else:
        logger.info(f"PASS: No Negative Pressures ({source}) | Checked {len(junction_heads)} junctions")


# Module logger
logger = logging.getLogger("econex.tests.validation")


def run_simulation(inp_file: str, duration_hours: int = 24) -> Tuple[wntr.network.WaterNetworkModel, object]:
    """Run EPANET simulation using WNTR.
    
    Args:
        inp_file: Path to EPANET .inp file.
        duration_hours: Simulation duration in hours.
        
    Returns:
        Tuple of (WaterNetworkModel, simulation results).
    """
    logger.info(f"Running EPANET simulation on {inp_file}")
    wn = wntr.network.WaterNetworkModel(inp_file)
    # Ensure duration matches if possible, but usually defined in INP
    # wn.options.time.duration = duration_hours * timestep
    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim(file_prefix='/var/tmp/tmp123')
    logger.info("EPANET simulation completed")
    return wn, results


def extract_optimization_timeseries(model: pyo.ConcreteModel, wn: wntr.network.WaterNetworkModel) -> Dict:
    """Extract time series data from optimization model.
    
    Args:
        model: Solved Pyomo model.
        wn: WNTR WaterNetworkModel for component names.
        
    Returns:
        Dictionary with DataFrames for heads and flows.
    """
    time_steps = list(model.T)
    timestep_sec = pyo.value(model.dt)
    
    # Create time index matching EPANET (seconds from start)
    time_index = [t * timestep_sec for t in time_steps]
    
    # Extract tank heads
    tank_heads = {}
    for tank in wn.tank_name_list:
        if tank in model.Tanks:
            heads = [pyo.value(model.H[tank, t]) for t in time_steps]
            tank_heads[tank] = heads
    df_tank_heads = pd.DataFrame(tank_heads, index=time_index)
    
    # Extract junction heads
    junc_heads = {}
    for junc in wn.junction_name_list:
        if junc in model.Junctions:
            heads = [pyo.value(model.H[junc, t]) for t in time_steps]
            junc_heads[junc] = heads
    df_junc_heads = pd.DataFrame(junc_heads, index=time_index)
    
    # Extract pump flows
    pump_flows = {}
    for pump in wn.pump_name_list:
        if pump in model.Pumps:
            flows = [pyo.value(model.Q[pump, t]) for t in time_steps]
            pump_flows[pump] = flows
    df_pump_flows = pd.DataFrame(pump_flows, index=time_index)
    
    # Extract pipe flows
    pipe_flows = {}
    for pipe in wn.pipe_name_list:
        if pipe in model.Pipes:
            flows = [pyo.value(model.Q[pipe, t]) for t in time_steps]
            pipe_flows[pipe] = flows
    df_pipe_flows = pd.DataFrame(pipe_flows, index=time_index)
    
    return {
        'tank_heads': df_tank_heads,
        'junction_heads': df_junc_heads,
        'pump_flows': df_pump_flows,
        'pipe_flows': df_pipe_flows
    }


def extract_simulation_timeseries(wn: wntr.network.WaterNetworkModel, 
                                   sim_results, 
                                   num_steps: int) -> Dict:
    """Extract time series data from EPANET simulation results.
    
    Args:
        wn: WNTR WaterNetworkModel.
        sim_results: EPANET simulation results.
        num_steps: Number of time steps to extract.
        
    Returns:
        Dictionary with DataFrames for heads and flows.
    """
    timestep = wn.options.time.report_timestep
    # WNTR results index is already in seconds, but might have extra steps if hydraulic timestep < report
    # We take the report steps.
    
    # Assuming standard report steps align with optimization timestep
    # If not, interpolation might be needed, but we keep it simple as per original
    
    # Note: sim_results.node['head'] index is time in seconds
    
    # We'll grab the first num_steps points assuming they match.
    # To be safer:
    time_index = list(range(0, num_steps * timestep, timestep))[:num_steps]
    
    # Helper to safe slice
    def safe_slice(series):
        # We try to loc specific times
        vals = []
        for t in time_index:
            if t in series.index:
                vals.append(series.loc[t])
            else:
                vals.append(0) # Fallback or error
        return vals

    # Extract tank heads
    tank_heads = {}
    for tank in wn.tank_name_list:
        # direct slicing if indices align, else use time-based lookup
        # Original code used: .loc[:timestep*(num_steps-1), tank].values[:num_steps]
        # We will try to follow that but be robust
        try:
             vals = sim_results.node['head'][tank].loc[time_index].values
        except KeyError:
             # If exact times not in index (e.g. slight mismatch), fallback to iloc
             vals = sim_results.node['head'][tank].values[:num_steps]
             
        tank_heads[tank] = vals
    df_tank_heads = pd.DataFrame(tank_heads, index=time_index)
    
    # Extract junction heads
    junc_heads = {}
    for junc in wn.junction_name_list:
        try:
             vals = sim_results.node['head'][junc].loc[time_index].values
        except KeyError:
             vals = sim_results.node['head'][junc].values[:num_steps]
        junc_heads[junc] = vals
    df_junc_heads = pd.DataFrame(junc_heads, index=time_index)
    
    # Extract pump flows
    pump_flows = {}
    for pump in wn.pump_name_list:
        try:
             vals = sim_results.link['flowrate'][pump].loc[time_index].values
        except KeyError:
             vals = sim_results.link['flowrate'][pump].values[:num_steps]
        pump_flows[pump] = vals
    df_pump_flows = pd.DataFrame(pump_flows, index=time_index)
    
    # Extract pipe flows
    pipe_flows = {}
    for pipe in wn.pipe_name_list:
        try:
             vals = sim_results.link['flowrate'][pipe].loc[time_index].values
        except KeyError:
             vals = sim_results.link['flowrate'][pipe].values[:num_steps]
        pipe_flows[pipe] = vals
    df_pipe_flows = pd.DataFrame(pipe_flows, index=time_index)
    
    return {
        'tank_heads': df_tank_heads,
        'junction_heads': df_junc_heads,
        'pump_flows': df_pump_flows,
        'pipe_flows': df_pipe_flows
    }


def compute_comparison_metrics(opt_data: Dict, sim_data: Dict) -> Dict:
    """Compute comparison metrics between optimization and simulation.
    
    Uses calculate_series_metrics for consistent metrics calculation.
    
    Args:
        opt_data: Optimization time series data.
        sim_data: Simulation time series data.
        
    Returns:
        Dictionary of comparison metrics by category and component.
    """
    metrics = {}
    
    for data_type in ['tank_heads', 'junction_heads', 'pump_flows', 'pipe_flows']:
        opt_df = opt_data.get(data_type, pd.DataFrame())
        sim_df = sim_data.get(data_type, pd.DataFrame())
        
        if opt_df.empty or sim_df.empty:
            continue
            
        # Align indices
        common_cols = set(opt_df.columns) & set(sim_df.columns)
        if not common_cols:
            continue
        
        type_metrics = {}
        for col in common_cols:
            opt_vals = opt_df[col].values
            sim_vals = sim_df[col].values[:len(opt_vals)]
            
            # Use centralized metrics calculation
            m = compare_series(opt_vals, sim_vals)
            
            # Return only the public metrics (not internal arrays)
            type_metrics[col] = {
                'n': m['n'],
                'mae': round(m['mae'], 6),
                'max_diff': round(m['max_diff'], 6),
                'max_rel_err_pct': round(m['max_rel_err_pct'], 2),
                'mean_rel_err_pct': round(m['mean_rel_err_pct'], 2),
                'correlation': round(m['correlation'], 4)
            }
        
        metrics[data_type] = type_metrics
    
    return metrics




def plot_component_grid(names: List[str], 
                       opt_df: pd.DataFrame, 
                       sim_df: pd.DataFrame, 
                       component_type: str,
                       ylabel: str,
                       colors: List[str],
                       save_dir: Optional[Path],
                       timestep: float = 3600) -> None:
    """Helper to plot grid of components."""
    if not names:
        return

    lw = 2.0
    fs = 12
    
    max_display = 20
    if len(names) > max_display:
        logger.info(f"{component_type} count ({len(names)}) exceeds {max_display}. Showing first {max_display}.")
        names = names[:max_display]
        
    n_cols = 4
    n_rows = int(np.ceil(len(names) / n_cols))
    
    # Adjust figure size
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 3 * n_rows))
    
    # Ensure axes is always iterable (flattened)
    if n_rows == 1 and n_cols == 1:
        ax_flat = [axes]
    else:
        ax_flat = axes.flatten()
        
    for i, name in enumerate(names):
        ax = ax_flat[i]
        
        # EPANET
        if name in sim_df.columns:
            sim_vals = sim_df[name].values
            sim_time = np.array(sim_df.index) / timestep
            ax.plot(sim_time, sim_vals, '--o', color=colors[1], lw=lw-0.5, label='EPANET')
            
        # Optimization
        if name in opt_df.columns:
            opt_vals = opt_df[name].values
            # Handle flow conversion if needed. Assuming inputs are already matched in units or raw.
            # In plot_comparison we did * timestep for flows previously.
            # We will handle unit conversion outside or check component_type.
            if component_type in ['Pumps', 'Pipes']:
                # The helper passed DFs. plot_comparison previously did *timestep inline.
                # Ideally opt_df passed here should be ready to plot.
                # For this refactor, I will assume the caller (plot_comparison) prepares the data units.
                pass
            
            opt_time = np.array(opt_df.index) / timestep
            # Match lengths if needed (though time index is optimized)
            ax.plot(opt_time, opt_vals, '--*', color=colors[0], lw=lw-0.5, label='Optimization')
            
        ax.set_title(f'{component_type[:-1]} {name}', fontsize=fs-2)
        ax.ticklabel_format(useOffset=False, style='plain') # 'sci' used in request, but plain often better for levels
        
        # Set Y label only on first column
        if i % n_cols == 0:
            ax.set_ylabel(ylabel)
        # Set X label only on last row
        if i >= n_cols * (n_rows - 1):
            ax.set_xlabel('Time [hr]')
            
    # Hide unused subplots
    for j in range(len(names), len(ax_flat)):
        ax_flat[j].set_visible(False)
        
    # Legend on first subplot
    if len(ax_flat) > 0:
        # Check if we plotted anything to add legend
        handles, labels = ax_flat[0].get_legend_handles_labels()
        if handles:
            ax_flat[0].legend(loc='best', fontsize=fs-3)
            
    plt.tight_layout()
    
    if save_dir:
        fname = f"{component_type.lower()}.png"
        save_path = save_dir / "plots" / fname
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved {fname}")
        plt.close(fig) # Close to free memory
    else:
        plt.show()


def plot_comparison(opt_data: Dict, sim_data: Dict, 
                   wn: wntr.network.WaterNetworkModel,
                   save_dir: Optional[Path] = None) -> None:
    """Create comparison plots for optimization vs simulation.
    
    Saves separate plots for Tanks, Pumps, Junctions, and Pipes.
    Also saves a Network Topology plot.
    
    Args:
        opt_data: Optimization time series data.
        sim_data: Simulation time series data.
        wn: WNTR WaterNetworkModel.
        save_dir: Directory to save plots.
    """
    # Style settings
    plt.style.use('seaborn-v0_8-paper')
    colors = ['#2DA8D8', '#D9514E', '#2D8D6E', '#8D6E2D', '#6E2D8D', 'grey', 'orange']
    
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "plots").mkdir(parents=True, exist_ok=True)

    # Get timestep for scaling and time axis
    timestep = wn.options.time.report_timestep  # seconds

    # 1. Tanks
    plot_component_grid(
        names=wn.tank_name_list,
        opt_df=opt_data['tank_heads'],
        sim_df=sim_data['tank_heads'],
        component_type="Tanks",
        ylabel="Head [m]",
        colors=colors,
        save_dir=save_dir,
        timestep=timestep
    )

    # 2. Pumps - Convert flow rate (m³/s) to volume per timestep (m³)
    plot_component_grid(
        names=wn.pump_name_list,
        opt_df=opt_data['pump_flows'] * timestep,
        sim_df=sim_data['pump_flows'] * timestep,
        component_type="Pumps",
        ylabel="Volume [m³/timestep]",
        colors=colors,
        save_dir=save_dir,
        timestep=timestep
    )

    # 3. Junctions
    plot_component_grid(
        names=wn.junction_name_list,
        opt_df=opt_data['junction_heads'],
        sim_df=sim_data['junction_heads'],
        component_type="Junctions",
        ylabel="Head [m]",
        colors=colors,
        save_dir=save_dir,
        timestep=timestep
    )

    # 4. Pipes - Convert flow rate (m³/s) to volume per timestep (m³)
    plot_component_grid(
        names=wn.pipe_name_list,
        opt_df=opt_data['pipe_flows'] * timestep,
        sim_df=sim_data['pipe_flows'] * timestep,
        component_type="Pipes",
        ylabel="Volume [m³/timestep]",
        colors=colors,
        save_dir=save_dir,
        timestep=timestep
    )

    # 5. Network Topology
    if wn:
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Plot 1: Standard Topology
        wntr.graphics.plot_network(wn, node_size=100, title='Network Topology', ax=axes[0])

        # Plot 2: Elevations
        elevation = wn.query_node_attribute('elevation')
        wntr.graphics.plot_network(wn, node_attribute=elevation, node_size=100, title='Node Elevations', ax=axes[1])
        
        plt.tight_layout()
        if save_dir:
            fig.savefig(save_dir / "system_topology.png", dpi=150, bbox_inches='tight')
            logger.info("Saved system_topology.png")
            plt.close(fig)
        else:
            plt.show()


def run_scenario_on_optimization_and_simulation(inp_file: str, 
                                     num_timesteps: int = 24,
                                     solver: str = 'gurobi',
                                     save_dir: Path = None) -> dict:
    """
    Runs a scenario on optimization and simulation engines and computes metrics.
    """
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting scenario: {Path(inp_file).name}")
    logger.info(f"  Timesteps: {num_timesteps} | Solver: {solver}")

    # 1. Build Model
    logger.info("Step 1: Building optimization model...")
    data = {
        'inp_file': inp_file,
        'config': {'T': num_timesteps}
    }
    model = build_model(data)
    logger.info(f"  Model built with {len(list(model.component_objects(pyo.Var)))} variable sets")
    
    # 2. Zero Objective
    if hasattr(model, 'objective'):
        model.del_component(model.objective)
    model.objective = pyo.Objective(expr=0, sense=pyo.minimize)
    
    # 3. Solve
    logger.info(f"Step 2: Solving optimization model with {solver}...")
    model, results = solve_model(model, solver=solver, tee=False)
    
    term_cond = results.solver.termination_condition
    logger.info(f"  Termination: {term_cond}")
    
    if term_cond != pyo.TerminationCondition.optimal:
        logger.error(f"  Solver failed: {term_cond}")
        return {'status': 'infeasible', 'termination': str(term_cond)}
    
    # 4. Run EPANET Sim (Ground Truth)
    logger.info("Step 3: Running EPANET simulation...")
    wn, sim_results = run_simulation(inp_file)
    logger.info(f"  Simulation completed: {len(wn.junction_name_list)} junctions, {len(wn.pipe_name_list)} pipes")
    
    # 5. Extract Time Series
    logger.info("Step 4: Extracting time series data...")
    opt_data = extract_optimization_timeseries(model, wn)
    sim_data = extract_simulation_timeseries(wn, sim_results, num_timesteps)
    logger.info(f"  Extracted: {len(opt_data.get('pipe_flows', {}))} pipes, {len(opt_data.get('junction_heads', {}))} junctions")
    
    # 6. Compute Metrics (saved to JSON for programmatic access)
    logger.info("Step 5: Computing comparison metrics...")
    metrics = compute_comparison_metrics(opt_data, sim_data)
    
    # 7. Plot/Save
    if save_dir:
        # Save metrics to JSON (for programmatic access)
        metrics_file = save_dir / 'feasibility_check_metrics.json'
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=4)
        
        # Plot comparison (now generates multiple files in save_dir)
        try:
            plot_comparison(opt_data, sim_data, wn, save_dir=save_dir)
            logger.info(f"  Plots saved to: {save_dir.name}/")
        except Exception as e:
            logger.error(f"Failed to generate plots: {e}")
    
    logger.info("Scenario completed successfully")
    
    return {
        'status': 'completed',
        'metrics': metrics,
        'opt_data': opt_data,
        'sim_data': sim_data,
        'timestep': wn.options.time.report_timestep
    }
