"""Preprocessing — network loading and run directory setup.

Loads both water (EPANET) and energy (OpenDSS) networks from a single
unified config and returns a data dict consumed by algorithm_tasks.build_model().
"""

import logging
from datetime import datetime
from pathlib import Path

import opendssdirect as dss

from src.helpers.utils import load_config

logger = logging.getLogger("econex.preprocessing")


def create_run_directory(output_dir: str) -> Path:
    """Create a timestamped run directory under output_dir.

    Args:
        output_dir: Base results directory (from config['paths']['output_dir']).

    Returns:
        Path to the created run_YYYYMMDD_HHMMSS/ directory.
    """
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(output_dir) / f"run_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "metadata").mkdir(exist_ok=True)
    logger.info(f"Created run directory: {run_dir}")
    return run_dir


def build_network_data(config: dict, project_root: Path) -> dict:
    """Load and validate network files referenced in config.

    Args:
        config:       Unified configuration dict (from config.yaml).
        project_root: Absolute path to the project root directory.

    Returns:
        Dict with keys 'water' and/or 'energy', each containing the
        file path and relevant config slice consumed by the sub-model builders.
    """
    data = {}

    if config.get("run_water") or config.get("run_nexus"):
        water_cfg = config.get("water", {})
        inp_path = project_root / water_cfg["network"]
        if not inp_path.exists():
            raise FileNotFoundError(f"Water network not found: {inp_path}")
        data["water"] = {
            "inp_file": str(inp_path),
            "config": config,
        }
        logger.info(f"Water network: {inp_path}")

    if config.get("run_energy") or config.get("run_nexus"):
        energy_cfg = config.get("energy", {})
        dss_path = project_root / energy_cfg["network"]
        if not dss_path.exists():
            raise FileNotFoundError(f"Energy network not found: {dss_path}")
        data["energy"] = _build_energy_data(energy_cfg, dss_path, config.get("T", 24))
        logger.info(f"Energy network: {dss_path}")

    return data


def _build_energy_data(energy_cfg: dict, dss_path: Path, T: int) -> dict:
    """Extract energy network parameters from config and DSS file.

    For now, network topology (buses, lines) is read from the energy config
    rather than parsed from the DSS file — DSS parsing via opendssdirect
    will be added once the energy workflow is validated end-to-end.

    Args:
        energy_cfg: config['energy'] section.
        dss_path:   Path to the master.dss file.
        T:          Number of time steps.

    Returns:
        Energy data dict consumed by models/energy.add_energy_submodel().
    """
    tech = energy_cfg.get("technologies", {})
    pv_cap = tech.get("pv", {}).get("capacity_kw", 0.0)
    pv_irr = tech.get("pv", {}).get("irradiance_profile", [0.0] * T)
    if not pv_irr:
        pv_irr = [0.0] * T

    stor = {
        "capacity_kwh":      tech.get("storage", {}).get("capacity_kwh", 200.0),
        "charge_efficiency":     tech.get("storage", {}).get("charge_efficiency", 0.95),
        "discharge_efficiency":  tech.get("storage", {}).get("discharge_efficiency", 0.95),
        "max_charge_kw":         tech.get("storage", {}).get("max_charge_kw", 50.0),
        "max_discharge_kw":      tech.get("storage", {}).get("max_discharge_kw", 50.0),
        "initial_soc_frac":      tech.get("storage", {}).get("initial_soc_fraction", 0.5),
    }

    cost_cfg = energy_cfg.get("cost", {})
    tariff = cost_cfg.get("grid_import_tariff", [0.1] * T)
    if not tariff:
        tariff = [0.1] * T

    dss.run_command(f"Compile [{dss_path}]")
    buses = dss.Circuit.AllBusNames()
    lines = []          # (n, m, R, X, I_max) — empty until DSS parsing is added
    
    # Placeholder loads on all buses
    loads = {b: [50.0] * T for b in buses}
    pv_profile = {b: [pv_cap * irr for irr in pv_irr] for b in buses}

    network_params = {
        "nominal_voltage_pu":  1.0, # Per unit is always 1.0 base
        "voltage_tolerance":   energy_cfg.get("voltage_tolerance", 0.10),
        "n_current_segments":  energy_cfg.get("n_current_segments", 5),
    }

    return {
        "dss_file":   str(dss_path),
        "buses":      buses,
        "lines":      lines,
        "loads":      loads,
        "pv_profile": pv_profile,
        "storage":    stor,
        "tariff":     tariff,
        "network":    network_params,
        "config":     energy_cfg,
    }
