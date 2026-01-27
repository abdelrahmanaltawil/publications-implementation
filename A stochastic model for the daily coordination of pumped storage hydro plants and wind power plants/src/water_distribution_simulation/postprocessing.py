"""Postprocessing Module for Water Distribution Simulation.

Result extraction, metrics computation, and data export.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import wntr

from src.helpers.utils import save_run_metadata as log_metadata, save_config

# Module logger
logger = logging.getLogger("wds.postprocessing")


def extract_results(results: wntr.sim.results.SimulationResults,
                    wn: wntr.network.WaterNetworkModel) -> dict:
    """Extract simulation results into organized DataFrames.

    Args:
        results: WNTR simulation results.
        wn: The water network model.

    Returns:
        Dictionary containing result DataFrames.
    """
    logger.info("Extracting simulation results")

    extracted = {
        'node': {},
        'link': {},
        'system_metadata': {}
    }

    # Node results
    extracted['node']['pressure'] = results.node['pressure']
    extracted['node']['head'] = results.node['head']
    extracted['node']['demand'] = results.node['demand']

    # Link results
    extracted['link']['flowrate'] = results.link['flowrate']
    extracted['link']['velocity'] = results.link['velocity']
    # Headloss may not be available with all simulators (e.g., WNTRSimulator)
    if 'headloss' in results.link:
        extracted['link']['headloss'] = results.link['headloss']

    logger.debug(f"Extracted {len(results.node['pressure'].columns)} node timeseries, "
                 f"{len(results.link['flowrate'].columns)} link timeseries")

    return extracted


def create_summary(run_id: str,
                   results: wntr.sim.results.SimulationResults,
                   wn: wntr.network.WaterNetworkModel,
                   min_pressure_threshold: float = 20.0) -> dict:
    """Compute resilience and performance metrics (Summary).

    Args:
        run_id: Run identifier.
        results: WNTR simulation results.
        wn: The water network model.
        min_pressure_threshold: Minimum acceptable pressure in meters (default 20m ≈ 28 psi).

    Returns:
        Dictionary of computed metrics/summary.
    """
    logger.info("Computing performance metrics (Summary)")

    metrics = {}

    # Pressure metrics (junctions only)
    junction_names = wn.junction_name_list
    if junction_names:
        pressure = results.node['pressure'][junction_names]

        metrics['pressure'] = {
            'min': float(pressure.min().min()),
            'max': float(pressure.max().max()),
            'mean': float(pressure.mean().mean()),
            'std': float(pressure.std().mean())
        }

        # Service satisfaction
        above_threshold = (pressure >= min_pressure_threshold).sum().sum()
        total_readings = pressure.size
        metrics['service_satisfaction'] = float(above_threshold / total_readings) if total_readings > 0 else 0.0

        # Critical nodes
        min_pressures = pressure.min()
        critical_nodes = min_pressures[min_pressures < min_pressure_threshold].index.tolist()
        metrics['critical_nodes'] = critical_nodes
        metrics['num_critical_nodes'] = len(critical_nodes)

    # Flow metrics
    pipe_names = wn.pipe_name_list
    if pipe_names:
        flowrate = results.link['flowrate'][pipe_names]
        velocity = results.link['velocity'][pipe_names]

        metrics['flow'] = {
            'max_flowrate_m3s': float(flowrate.abs().max().max()),
            'max_velocity_ms': float(velocity.abs().max().max()),
            'mean_velocity_ms': float(velocity.abs().mean().mean())
        }

    # Demand satisfaction
    demand = results.node['demand']
    if junction_names:
        junction_demand = demand[junction_names]
        total_demand = float(junction_demand[junction_demand > 0].sum().sum())
        metrics['total_demand_m3'] = total_demand
    
    # System metadata
    system_metadata = {
        'num_nodes': wn.num_nodes,
        'num_links': wn.num_links,
        'num_junctions': len(wn.junction_name_list),
        'num_tanks': len(wn.tank_name_list),
        'num_reservoirs': len(wn.reservoir_name_list),
        'num_pipes': len(wn.pipe_name_list),
        'num_pumps': wn.num_pumps,
        'num_valves': wn.num_valves,
        'duration_hours': wn.options.time.duration / 3600,
        'hydraulic_timestep_hours': wn.options.time.hydraulic_timestep / 3600,
        'quality_timestep_hours': wn.options.time.quality_timestep / 3600,
        'pattern_timestep_hours': wn.options.time.pattern_timestep / 3600,
        'report_timestep_hours': wn.options.time.report_timestep / 3600
    }
    
    # Finalize summary structure
    summary = {
        'run_id': run_id,
        'timestamp': datetime.now().isoformat(),
        'network': system_metadata,
        'metrics': metrics 
    }

    logger.info(f"Summary computed: service_satisfaction={metrics.get('service_satisfaction', 'N/A'):.2%}")

    return summary


def save_results(extracted: dict, summary: dict, run_dir: Path) -> None:
    """Save results and summary to files.

    Args:
        extracted: Extracted results from extract_results().
        summary: Computed summary/metrics from create_summary().
        run_dir: Directory to save results.
    """

    logger.info(f"Saving results to: {run_dir}")

    # Save node results
    node_dir = run_dir / 'nodes'
    node_dir.mkdir(exist_ok=True)
    for name, df in extracted['node'].items():
        df.to_csv(node_dir / f'{name}.csv')
        logger.debug(f"Saved node/{name}.csv")

    # Save link results
    link_dir = run_dir / 'links'
    link_dir.mkdir(exist_ok=True)
    for name, df in extracted['link'].items():
        df.to_csv(link_dir / f'{name}.csv')
        logger.debug(f"Saved link/{name}.csv")

    # Save summary
    with open(run_dir / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    logger.debug("Saved summary.json")

    logger.info(f"All results saved to: {run_dir}")
