"""Preprocessing Module for Water Distribution Simulation.

Network loading, demand pattern configuration, and pump control setup using WNTR.
"""

import logging
import shutil
from pathlib import Path
from typing import Optional

import yaml
import wntr
from datetime import datetime

# Module logger
logger = logging.getLogger("wds.preprocessing")

project_root = Path(__file__).resolve().parents[2]


from src.helpers.utils import load_config


def create_run_directory(output_dir: str) -> Path:
    """Create a timestamped directory for saving results.

    Args:
        output_dir: Base output directory path.

    Returns:
        Path to the created run directory.
    """
    base_path = Path(output_dir)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = base_path / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created run directory: {run_dir}")
    return run_dir


def save_inp_file(config: dict, run_dir: Path) -> None:
    """Save the .inp file to the run directory"""
    try:
        target_path = run_dir / Path(config['network']['inp_file']).name
        shutil.copy(config['network']['inp_file'], target_path)
        logger.debug(f"Copied original config to {target_path}")
    except Exception as e:
        logger.warning(f"Could not copy original config file: {e}")


def load_network(inp_file_path: str) -> wntr.network.WaterNetworkModel:
    """Load water network model from EPANET .inp file.

    Args:
        inp_file_path: Path to the EPANET .inp file.

    Returns:
        The water network model ready for simulation.

    Raises:
        ValueError: If no inp_file is specified in config.
    """
    if not inp_file_path:
        raise ValueError("No inp_file specified in config. An EPANET .inp file is required.")

    logger.info(f"Loading network from EPANET file: {inp_file_path}")
    wn = wntr.network.WaterNetworkModel(inp_file_path)
    logger.debug(f"Network loaded: {wn.num_nodes} nodes, {wn.num_links} links")     

    return wn