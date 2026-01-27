"""Preprocessing Module for EcoNex Optimization.

Network topology construction and data preparation.
"""

import logging
from datetime import datetime
from pathlib import Path
from src.helpers.utils import load_config

# Module logger
logger = logging.getLogger("econex.preprocessing")


def create_run_directory(output_dir: str, run_id: str = None) -> Path:
    """Create a run directory for storing results.
    
    Args:
        output_dir: Base output directory.
        run_id: Run identifier (defaults to timestamp).
    
    Returns:
        Path to created run directory.
    """
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    run_dir = Path(output_dir) / str('run_'+run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Created run directory: {run_dir}")
    return run_dir


def build_network_data(config: dict) -> dict:
    """Prepare network data structure for Pyomo model.
    
    For the hydraulic model, this primarily involves validating the INP file path.
    
    Args:
        config: Configuration dictionary.
    
    Returns:
        Dictionary containing configuration and file paths.
    """
    logger.info("Building network data structure")
    
    inp_file_path = Path(__file__).parents[2] / config['inp_file']
    
    if not inp_file_path.exists():
        raise FileNotFoundError(f"Input file not found at: {inp_file_path}")

    logger.info(f"Using EPANET input file: {inp_file_path}")

    return {
        'inp_file': str(inp_file_path),
        'T': config.get('T', 24),
        'config': config
    }
