"""Postprocessing Module for EcoNex.

Solution extraction, results formatting, and metadata logging.
"""

import json
import logging
import shutil
import pandas as pd
import pyomo.environ as pyo
from pathlib import Path
from src.helpers.utils import save_run_metadata as log_metadata, save_config

# Module logger
logger = logging.getLogger("econex.postprocessing")


def extract_solution(model: pyo.ConcreteModel) -> dict:
    """Extract optimal variable values from solved hydraulic model.

    Args:
        model: Solved Pyomo ConcreteModel.

    Returns:
        Dictionary containing flows, heads, and other statuses.
    """
    # Check if model has solution
    # Try to access one variable to check if initialized
    try:
        pyo.value(model.objective)
    except (ValueError, TypeError):
        logger.warning("Model has no solution values (uninitialized). Returning empty results.")
        return {'objective': None, 'flows': [], 'heads': [], 'pump_status': []}

    results = {
        'objective': pyo.value(model.objective),
        'flows': [],
        'heads': [],
        'pump_status': [],
        'slack_pos': [],
        'slack_neg': []
    }
    
    # Extract Flows
    logger.debug("Extracting flows")
    for l in model.Links:
        for t in model.T:
            if (l, t) in model.Q:
                 val = pyo.value(model.Q[l, t])
                 results['flows'].append({
                     'link': l, 'time': t, 'flow_rate': round(val, 4)
                 })
            
    # Extract Heads
    logger.debug("Extracting heads")
    for n in model.Nodes:
        for t in model.T:
            if (n, t) in model.H:
                val = pyo.value(model.H[n, t])
                results['heads'].append({
                    'node': n, 'time': t, 'head': round(val, 4)
                })
            
    # Extract Pump/Valve Status
    logger.debug("Extracting pump status")
    for p in model.Pumps:
        for t in model.T:
            try:
                val = pyo.value(model.Status[p, t])
                results['pump_status'].append({
                    'pump': p, 'time': t, 'status': int(round(val))
                })
            except:
                pass 

    # Extract Slacks
    logger.debug("Extracting slacks")
    for n in model.Junctions:
        for t in model.T:
            if (n, t) in model.SlackPos:
                val_pos = pyo.value(model.SlackPos[n, t])
                val_neg = pyo.value(model.SlackNeg[n, t])
                if val_pos > 1e-6 or val_neg > 1e-6:
                    results['slack_pos'].append({'node': n, 'time': t, 'value': val_pos})
                    results['slack_neg'].append({'node': n, 'time': t, 'value': val_neg})

    logger.info(f"Solution extracted. Objective: {results['objective']}")
    return results


def create_summary(run_id: str, model: pyo.ConcreteModel, results: dict, solver_results) -> dict:
    """Compute summary metrics from simulation results.

    Args:
        run_id: Run identifier.
        model: Pyomo model instance.
        results: Dictionary from extract_solution().
        solver_results: Solver results from solve_model().

    Returns:
        Summary dictionary.
    """
    logger.info("Creating simulation summary")
    
    num_vars = sum(1 for _ in model.component_data_objects(pyo.Var, active=True))
    num_constraints = sum(1 for _ in model.component_data_objects(pyo.Constraint, active=True))

    summary = {
        'run_id': run_id,
        'solver_status': str(solver_results.solver.status),
        'termination_condition': str(solver_results.solver.termination_condition),
        'objective_value': results['objective'],
        'solver_time_s': getattr(solver_results.solver, 'time', "time not found"),
        'num_variables': num_vars,
        'num_constraints': num_constraints
    }
    
    return summary


def save_results(results: dict, summary: dict, run_dir: Path) -> str:
    """Save extracted results and summary to files.

    Args:
        results: Dictionary from extract_solution().
        summary: Summary dictionary from create_summary().
        run_dir: Path to run directory.

    Returns:
        Path to run directory.
    """
    logger.info(f"Saving results to: {run_dir}")
    
    if results['flows']:
        df_flows = pd.DataFrame(results['flows'])
        df_flows.to_csv(run_dir / 'flows.csv', index=False)
        
    if results['heads']:
        df_heads = pd.DataFrame(results['heads'])
        df_heads.to_csv(run_dir / 'heads.csv', index=False)
        
    if results['pump_status']:
        df_status = pd.DataFrame(results['pump_status'])
        df_status.to_csv(run_dir / 'pump_status.csv', index=False)

    if results.get('slack_pos'):
        pd.DataFrame(results['slack_pos']).to_csv(run_dir / 'slack_pos.csv', index=False)
    if results.get('slack_neg'):
        pd.DataFrame(results['slack_neg']).to_csv(run_dir / 'slack_neg.csv', index=False)

    # Add run information content to summary just before saving
    summary['run_id'] = run_dir.name

    with open(run_dir / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"All results saved to {run_dir}")
    
    return str(run_dir)


def save_inp_file(run_dir: Path, inp_file_path: str) -> None:
    """Save a copy of the input EPANET file to the run directory.

    Args:
        run_dir: Path to the run directory.
        inp_file_path: Path to the input EPANET file.
    """
    try:
        source_path = Path(inp_file_path)
        if source_path.exists():
            shutil.copy2(source_path, run_dir / source_path.name)
            logger.info(f"Saved input file to {run_dir / source_path.name}")
        else:
            logger.warning(f"Input file not found at {inp_file_path}, skipping save.")
    except Exception as e:
        logger.error(f"Failed to save input file: {e}")