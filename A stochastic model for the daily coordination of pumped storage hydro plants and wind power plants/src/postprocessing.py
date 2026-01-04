"""
Postprocessing Module for EcoNex.

Solution extraction, results formatting, and metadata logging.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyomo.environ as pyo

# Module logger
logger = logging.getLogger("econex.postprocessing")


def extract_solution(model: pyo.ConcreteModel) -> dict:
    """
    Extract optimal variable values from solved model.
    
    Parameters
    ----------
    model : pyo.ConcreteModel
        Solved Pyomo ConcreteModel.
    
    Returns
    -------
    dict
        Dictionary containing flows, storage, and objective value.
    """
    logger.info("Extracting solution from model")
    
    results = {
        'objective': pyo.value(model.objective),
        'flows': [],
        'storage': [],
        'grid': [],
        'treatment': [],
        'pumping': []
    }
    
    logger.debug("Extracting flow variables")
    for (i, j) in model.A:
        for l in model.L:
            for t in model.T:
                val = pyo.value(model.x[i, j, l, t])
                if val > 1e-6:
                    results['flows'].append({
                        'from': i, 'to': j, 'layer': l, 'time': t, 'value': round(val, 4)
                    })
    
    logger.debug(f"Extracted {len(results['flows'])} non-zero flow entries")
    
    logger.debug("Extracting storage variables")
    for n in model.N:
        for l in model.L:
            for t in model.T:
                val = pyo.value(model.h[n, l, t])
                results['storage'].append({
                    'node': n, 'layer': l, 'time': t, 'value': round(val, 4)
                })
    
    logger.debug("Extracting grid import/export")
    for t in model.T:
        results['grid'].append({
            'time': t,
            'import': round(pyo.value(model.grid_import[t]), 4),
            'export': round(pyo.value(model.grid_export[t]), 4)
        })
    
    logger.debug("Extracting treatment flows")
    for t in model.T:
        results['treatment'].append({
            'time': t,
            'waste_in': round(pyo.value(model.treatment_in[t]), 4),
            'potable_out': round(pyo.value(model.treatment_out[t]), 4)
        })
    
    logger.debug("Extracting pumping energy")
    for n in model.N:
        for t in model.T:
            val = pyo.value(model.pump_energy[n, t])
            if val > 1e-6:
                results['pumping'].append({
                    'node': n, 'time': t, 'energy': round(val, 4)
                })
    
    logger.info(f"Solution extracted: objective=${results['objective']:.2f}, "
                f"{len(results['flows'])} flows, {len(results['pumping'])} pump entries")
    
    return results


def create_run_directory(output_dir: str, run_id: str = None) -> Path:
    """
    Create a run directory for storing results.
    
    Parameters
    ----------
    output_dir : str
        Base output directory.
    run_id : str, optional
        Run identifier (defaults to timestamp).
    
    Returns
    -------
    Path
        Path to created run directory.
    """
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    run_dir = Path(output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Created run directory: {run_dir}")
    return run_dir


def save_config(config: dict, run_dir: Path, config_path: str = None):
    """
    Save configuration to the run directory.
    
    Parameters
    ----------
    config : dict
        Configuration dictionary.
    run_dir : Path
        Run directory path.
    config_path : str, optional
        Original config file path to copy.
    """
    # Save as JSON for easy programmatic access
    config_json_path = run_dir / 'config.json'
    with open(config_json_path, 'w') as f:
        json.dump(config, f, indent=2)
    logger.debug(f"Saved config.json to {run_dir}")
    
    # Also copy original YAML if provided
    if config_path is not None:
        config_yaml_path = run_dir / 'config.yaml'
        shutil.copy(config_path, config_yaml_path)
        logger.debug(f"Copied original config.yaml to {run_dir}")


def save_results(results: dict, run_dir: Path) -> str:
    """
    Save extracted results to files.
    
    Parameters
    ----------
    results : dict
        Dictionary from extract_solution().
    run_dir : Path
        Path to run directory.
    
    Returns
    -------
    str
        Path to run directory.
    """
    logger.info(f"Saving results to: {run_dir}")
    
    if results['flows']:
        df_flows = pd.DataFrame(results['flows'])
        df_flows.to_csv(run_dir / 'flows.csv', index=False)
        logger.debug(f"Saved flows.csv ({len(df_flows)} rows)")
    
    if results['storage']:
        df_storage = pd.DataFrame(results['storage'])
        df_storage.to_csv(run_dir / 'storage.csv', index=False)
        logger.debug(f"Saved storage.csv ({len(df_storage)} rows)")
    
    if results['grid']:
        df_grid = pd.DataFrame(results['grid'])
        df_grid.to_csv(run_dir / 'grid.csv', index=False)
        logger.debug("Saved grid.csv")
    
    if results['treatment']:
        df_treatment = pd.DataFrame(results['treatment'])
        df_treatment.to_csv(run_dir / 'treatment.csv', index=False)
        logger.debug("Saved treatment.csv")
    
    summary = {
        'run_id': run_dir.name,
        'objective_value': results['objective'],
        'timestamp': datetime.now().isoformat(),
        'num_flows': len(results['flows']),
        'num_storage_entries': len(results['storage'])
    }
    with open(run_dir / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    logger.debug("Saved summary.json")
    
    logger.info(f"All results saved to {run_dir}")
    
    return str(run_dir)


def log_metadata(model: pyo.ConcreteModel, solver_results, run_dir: Path):
    """
    Log solver status, timing, and model statistics.
    
    Parameters
    ----------
    model : pyo.ConcreteModel
        The Pyomo model.
    solver_results : SolverResults
        Results object from solver.
    run_dir : Path
        Run directory path.
    """
    logger.debug("Logging solver metadata")
    
    num_vars = sum(1 for _ in model.component_data_objects(pyo.Var, active=True))
    num_constraints = sum(1 for _ in model.component_data_objects(pyo.Constraint, active=True))
    
    metadata = {
        'solver_status': str(solver_results.solver.status),
        'termination_condition': str(solver_results.solver.termination_condition),
        'objective_value': pyo.value(model.objective),
        'num_variables': num_vars,
        'num_constraints': num_constraints,
        'timestamp': datetime.now().isoformat()
    }
    
    if hasattr(solver_results.solver, 'time'):
        metadata['solve_time_seconds'] = solver_results.solver.time
    
    output_path = run_dir / 'metadata.json'
    with open(output_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Metadata saved to {output_path}")


def print_summary(results: dict):
    """Print a human-readable summary of the optimization results."""
    logger.info("Generating results summary")
    
    total_import = sum(g['import'] for g in results['grid'])
    total_export = sum(g['export'] for g in results['grid'])
    total_treated = sum(t['waste_in'] for t in results['treatment'])
    
    summary_lines = [
        "",
        "=" * 60,
        "EcoNex Optimization Results Summary",
        "=" * 60,
        f"Objective Value (Total Cost): ${results['objective']:.2f}",
        f"Number of active flow arcs: {len(results['flows'])}",
        "",
        "Grid Energy:",
        f"  Total Import: {total_import:.2f} kWh",
        f"  Total Export: {total_export:.2f} kWh",
        "",
        "Water Treatment:",
        f"  Total Waste Treated: {total_treated:.2f} m³",
        "=" * 60,
        ""
    ]
    
    for line in summary_lines:
        print(line)
    
    logger.debug(f"Summary: cost=${results['objective']:.2f}, "
                 f"grid_import={total_import:.2f}kWh, treated={total_treated:.2f}m³")
