
import logging
import shutil
import yaml
import json
import sys
import os
import platform
import getpass
import socket
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

def load_config(config_path: str) -> dict:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Configuration dictionary.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
    """
    logger.info(f"Loading configuration from: {config_path}")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        logger.info("Please ensure the configuration file exists.")
        raise
    
    logger.debug(f"Configuration loaded with {len(config)} top-level keys")
    return config


def get_git_revision_hash() -> str:
    """Retrieve the current git commit hash for traceability.

    Returns:
        The git ref hash or 'unknown'.
    """
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL).decode('ascii').strip()
    except Exception as e:
        logger.warning(f"Could not retrieve git hash: {e}")
        return "unknown"


def save_run_metadata(run_dir: Path) -> None:
    """Log and save system-level run metadata.

    Args:
        run_dir: Run directory path.
    """
    logger.debug("Logging run metadata")
    
    metadata = {
        "experiment_id": run_dir.name,
        "execution_start_time": datetime.fromtimestamp(run_dir.stat().st_ctime).isoformat(),
        "execution_duration_min": round((datetime.now() - datetime.fromtimestamp(run_dir.stat().st_ctime)).total_seconds() / 60, 3),
        "timestamp": datetime.now().isoformat(),
        "git_commit": get_git_revision_hash(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "user": getpass.getuser(),
        "hostname": socket.gethostname(),
        "working_directory": os.getcwd(),
        "command": " ".join(sys.argv),
    }

    output_path = run_dir / 'metadata' / 'run_metadata.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    
    logger.info(f"Metadata saved to {output_path}")


def save_config(run_dir: Path, config_path: str) -> None:
    """Save the original configuration file to the run directory.
    
    This function ensures reproducibility by saving the exact configuration file 
    used to run the simulation, without any runtime mutations.

    Args:
        run_dir: Run directory path.
        config_path: Path to the original configuration file to copy.
    """
    if config_path:
        try:
            target_path = run_dir / 'config.yaml'
            shutil.copy(config_path, target_path)
            logger.debug(f"Copied original config to {target_path}")
        except Exception as e:
            logger.warning(f"Could not copy original config file: {e}")



