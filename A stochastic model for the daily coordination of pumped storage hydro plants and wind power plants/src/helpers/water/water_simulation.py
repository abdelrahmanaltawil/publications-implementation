"""Water network simulation helper (WNTR-based).

Used as a pre-optimization network exploration tool and as a post-optimization
validation tool to compare optimal schedules against physics-based simulation.
Not a standalone workflow — call these functions from tests or workflow.py.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import wntr

logger = logging.getLogger("econex.helpers.water_simulation")


# ---------------------------------------------------------------------------
# Network loading
# ---------------------------------------------------------------------------

def load_water_network(inp_file: str) -> wntr.network.WaterNetworkModel:
    """Load an EPANET .inp file into a WNTR WaterNetworkModel.

    Args:
        inp_file: Path to the EPANET .inp file.

    Returns:
        Configured WaterNetworkModel ready for simulation.
    """
    if not inp_file:
        raise ValueError("No inp_file specified.")
    logger.info(f"Loading water network: {inp_file}")
    wn = wntr.network.WaterNetworkModel(inp_file)
    logger.debug(f"Loaded: {wn.num_nodes} nodes, {wn.num_links} links")
    return wn


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def run_water_simulation(
    wn: wntr.network.WaterNetworkModel,
    simulator_type: str = "wntr",
) -> wntr.sim.results.SimulationResults:
    """Run a hydraulic simulation using WNTR or the EPANET toolkit.

    Args:
        wn:              Configured WaterNetworkModel.
        simulator_type:  'wntr' (pure Python) or 'epanet' (EPANET toolkit).

    Returns:
        SimulationResults with node and link DataFrames.
    """
    logger.info(f"Running water simulation ({simulator_type.upper()})")

    if simulator_type.lower() == "epanet":
        sim = wntr.sim.EpanetSimulator(wn)
    else:
        sim = wntr.sim.WNTRSimulator(wn)

    results = sim.run_sim()
    logger.info("Water simulation completed")
    _log_simulation_summary(results, wn)
    return results


# ---------------------------------------------------------------------------
# Result extraction and summary
# ---------------------------------------------------------------------------

def extract_water_results(
    results: wntr.sim.results.SimulationResults,
    wn: wntr.network.WaterNetworkModel,
) -> dict:
    """Organise WNTR results into a nested dict of DataFrames.

    Returns:
        {'node': {'pressure': df, 'head': df, 'demand': df},
         'link': {'flowrate': df, 'velocity': df, ...}}
    """
    extracted = {"node": {}, "link": {}}
    extracted["node"]["pressure"] = results.node["pressure"]
    extracted["node"]["head"] = results.node["head"]
    extracted["node"]["demand"] = results.node["demand"]
    extracted["link"]["flowrate"] = results.link["flowrate"]
    extracted["link"]["velocity"] = results.link["velocity"]
    if "headloss" in results.link:
        extracted["link"]["headloss"] = results.link["headloss"]
    return extracted


def create_water_summary(
    run_id: str,
    results: wntr.sim.results.SimulationResults,
    wn: wntr.network.WaterNetworkModel,
    min_pressure_threshold: float = 20.0,
) -> dict:
    """Compute hydraulic performance metrics.

    Args:
        run_id:                  Run identifier string.
        results:                 WNTR SimulationResults.
        wn:                      WaterNetworkModel.
        min_pressure_threshold:  Minimum acceptable pressure (metres).

    Returns:
        Summary dict with pressure, flow, and service metrics.
    """
    metrics = {}
    junction_names = wn.junction_name_list

    if junction_names:
        pressure = results.node["pressure"][junction_names]
        metrics["pressure"] = {
            "min": float(pressure.min().min()),
            "max": float(pressure.max().max()),
            "mean": float(pressure.mean().mean()),
            "std": float(pressure.std().mean()),
        }
        above = (pressure >= min_pressure_threshold).sum().sum()
        metrics["service_satisfaction"] = float(above / pressure.size) if pressure.size else 0.0
        min_p = pressure.min()
        metrics["critical_nodes"] = min_p[min_p < min_pressure_threshold].index.tolist()

    pipe_names = wn.pipe_name_list
    if pipe_names:
        flowrate = results.link["flowrate"][pipe_names]
        velocity = results.link["velocity"][pipe_names]
        metrics["flow"] = {
            "max_flowrate_m3s": float(flowrate.abs().max().max()),
            "max_velocity_ms": float(velocity.abs().max().max()),
            "mean_velocity_ms": float(velocity.abs().mean().mean()),
        }

    return {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "network": {
            "num_nodes": wn.num_nodes,
            "num_links": wn.num_links,
            "duration_hours": wn.options.time.duration / 3600,
        },
        "metrics": metrics,
    }


def save_water_results(extracted: dict, summary: dict, run_dir: Path) -> None:
    """Save water simulation results to run_dir/water/.

    Args:
        extracted:  From extract_water_results().
        summary:    From create_water_summary().
        run_dir:    Top-level run directory.
    """
    water_dir = run_dir / "water"
    water_dir.mkdir(parents=True, exist_ok=True)

    node_dir = water_dir / "nodes"
    node_dir.mkdir(exist_ok=True)
    for name, df in extracted["node"].items():
        df.to_csv(node_dir / f"{name}.csv")

    link_dir = water_dir / "links"
    link_dir.mkdir(exist_ok=True)
    for name, df in extracted["link"].items():
        df.to_csv(link_dir / f"{name}.csv")

    with open(water_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    logger.info(f"Water simulation results saved to {water_dir}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _log_simulation_summary(
    results: wntr.sim.results.SimulationResults,
    wn: wntr.network.WaterNetworkModel,
) -> None:
    junction_names = wn.junction_name_list
    if junction_names:
        p = results.node["pressure"][junction_names]
        logger.info(
            f"Junction pressures: min={p.min().min():.2f}m, "
            f"max={p.max().max():.2f}m, mean={p.mean().mean():.2f}m"
        )
    pipe_names = wn.pipe_name_list
    if pipe_names:
        max_flow = results.link["flowrate"][pipe_names].abs().max().max()
        logger.info(f"Max pipe flow: {max_flow:.4f} m³/s")
