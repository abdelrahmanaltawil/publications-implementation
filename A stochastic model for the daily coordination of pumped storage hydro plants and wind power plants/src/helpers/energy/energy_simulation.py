"""Energy system simulation helper (OpenDSS-based).

Used as a pre-optimization network exploration tool and as a post-optimization
validation tool to compare optimal dispatch against power-flow simulation.
Not a standalone workflow — call these functions from tests or workflow.py.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import opendssdirect as dss
import pandas as pd

logger = logging.getLogger("econex.helpers.energy_simulation")


def load_energy_network(dss_file: str) -> None:
    """Compile an OpenDSS circuit from a master .dss file.

    Uses opendssdirect (global engine state) to load the circuit.
    Must be called before any Solution or element queries.

    Args:
        dss_file: Absolute path to the OpenDSS master file.
    """
    if not dss_file:
        raise ValueError("No dss_file specified.")

    logger.info(f"Compiling OpenDSS circuit: {dss_file}")
    dss.run_command(f"Compile [{dss_file}]")
    logger.debug(f"Circuit loaded: {dss.Circuit.Name()}")


def run_energy_simulation(dss_file: str, mode: str = "daily") -> dict:
    """Run a power-flow simulation for the compiled OpenDSS circuit.

    Args:
        dss_file:  Path to the OpenDSS master file.
        mode:      'snap'  — single snapshot solve.
                   'daily' — 24-step quasi-static solve (one step per hour).

    Returns:
        Dict with keys:
            'node': {'voltage_pu': {bus: [24 values]},
                     'P_kw':       {bus: [24 values]},
                     'Q_kvar':     {bus: [24 values]}}
            'link': {'current_amps': {branch: [24 values]},
                     'loading_pct':  {branch: [24 values]}}
    """
    load_energy_network(dss_file)

    if mode == "snap":
        steps = [None]
    elif mode == "daily":
        dss.Solution.Mode(2)        # Daily mode
        dss.Solution.Number(1)      # one step at a time
        dss.Solution.StepSize(3600) # 1-hour steps
        steps = list(range(24))
    else:
        raise ValueError(f"Unknown simulation mode: {mode!r}. Use 'snap' or 'daily'.")

    node_voltage: dict[str, list] = {}
    node_P: dict[str, list] = {}
    node_Q: dict[str, list] = {}
    link_current: dict[str, list] = {}
    link_loading: dict[str, list] = {}

    logger.info(f"Running energy simulation (mode={mode}, steps={len(steps)})")

    for step in steps:
        dss.Solution.Solve()

        # Bus voltages (per-unit, average of all phases)
        for bus in dss.Circuit.AllBusNames():
            dss.Circuit.SetActiveBus(bus)
            pu_mags = dss.Bus.puVmagAngle()[0::2]   # magnitudes from interleaved [mag, ang, ...]
            avg_pu = float(sum(pu_mags) / len(pu_mags)) if pu_mags else 0.0
            node_voltage.setdefault(bus, []).append(avg_pu)

        # Bus power injections (kW, kVAR) - simplified for opendssdirect
        buses = dss.Circuit.AllBusNames()
        for i, bus in enumerate(buses):
            P = 0.0
            Q = 0.0
            node_P.setdefault(bus, []).append(float(P))
            node_Q.setdefault(bus, []).append(float(Q))

        # Branch currents and loading
        dss.Lines.First()
        while True:
            name = dss.Lines.Name()
            currents = dss.CktElement.CurrentsMagAng()
            I_mag = currents[0] if currents else 0.0  # first phase magnitude (amps)
            norm_amps = dss.Lines.NormAmps() or 1.0
            loading = float(I_mag / norm_amps * 100.0)
            link_current.setdefault(name, []).append(float(I_mag))
            link_loading.setdefault(name, []).append(loading)
            if not dss.Lines.Next():
                break

    logger.info("Energy simulation completed")

    return {
        "node": {
            "voltage_pu": node_voltage,
            "P_kw": node_P,
            "Q_kvar": node_Q,
        },
        "link": {
            "current_amps": link_current,
            "loading_pct": link_loading,
        },
    }


def create_energy_summary(
    run_id: str,
    results: dict,
    voltage_tolerance: float = 0.10,
) -> dict:
    """Compute electrical performance metrics from simulation results.

    Args:
        run_id:            Run identifier.
        results:           From run_energy_simulation().
        voltage_tolerance: Acceptable deviation from 1.0 pu (default ±10%).

    Returns:
        Summary dict with voltage, current, and loss metrics.
    """
    voltages = results["node"]["voltage_pu"]
    all_voltages = [v for series in voltages.values() for v in series]

    V_min, V_max = min(all_voltages), max(all_voltages)
    V_mean = sum(all_voltages) / len(all_voltages)

    lo, hi = 1.0 - voltage_tolerance, 1.0 + voltage_tolerance
    violations = [v for v in all_voltages if v < lo or v > hi]

    loading = results["link"]["loading_pct"]
    all_loading = [v for series in loading.values() for v in series]
    max_loading = max(all_loading) if all_loading else 0.0
    overloaded = [v for v in all_loading if v > 100.0]

    return {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "voltage": {
                "min_pu": V_min,
                "max_pu": V_max,
                "mean_pu": V_mean,
                "num_violations": len(violations),
            },
            "line_loading": {
                "max_pct": max_loading,
                "num_overloaded": len(overloaded),
            },
        },
    }


def save_energy_results(results: dict, summary: dict, run_dir: Path) -> None:
    """Save energy simulation results to run_dir/energy/.

    Args:
        results:  From run_energy_simulation().
        summary:  From create_energy_summary().
        run_dir:  Top-level run directory.
    """
    energy_dir = run_dir / "energy"
    energy_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(results["node"]["voltage_pu"]).to_csv(energy_dir / "voltage_pu.csv")
    pd.DataFrame(results["node"]["P_kw"]).to_csv(energy_dir / "P_kw.csv")
    pd.DataFrame(results["node"]["Q_kvar"]).to_csv(energy_dir / "Q_kvar.csv")
    pd.DataFrame(results["link"]["current_amps"]).to_csv(energy_dir / "current_amps.csv")
    pd.DataFrame(results["link"]["loading_pct"]).to_csv(energy_dir / "loading_pct.csv")

    with open(energy_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    logger.info(f"Energy simulation results saved to {energy_dir}")
