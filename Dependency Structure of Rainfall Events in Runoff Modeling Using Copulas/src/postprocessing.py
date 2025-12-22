# imports
import datetime
import yaml
import logging
import subprocess
import sys
import os
import platform
import socket
import getpass
import pathlib

# local imports

def get_git_revision_hash() -> str:
    """Retrieve the current git commit hash for traceability."""
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL).decode('ascii').strip()
    except Exception as e:
        logging.warning(f"Could not retrieve git hash: {e}")
        return "unknown"

def save_run_metadata(save_path: pathlib.Path, metadata: dict, experiment_parameters: dict, logger: logging.Logger) -> None:
    """Saves run environment and versioning, details."""
    try:
        start_time = datetime.datetime.fromisoformat(metadata["execution_start_time"])
        end_time = datetime.datetime.now()
        duration_min = (end_time - start_time).total_seconds() / 60.0

        metadata = {
            "experiment_id": save_path.parts[-1].split(" -- ")[-1],
            "execution_start_time": metadata["execution_start_time"],
            "execution_end_time": end_time.isoformat(),
            "execution_duration_min": round(duration_min, 2),
            "timestamp": end_time.isoformat(),
            "git_commit": get_git_revision_hash(),
            "python_version": sys.version,
            "platform": platform.platform(),
            "user": getpass.getuser(),
            "hostname": socket.gethostname(),
            "working_directory": os.getcwd(),
            "command": " ".join(sys.argv),
        }

        # Save run metadata        
        meta_path = save_path / "00_run_metadata.yaml"
        with open(meta_path, "w") as f:
            yaml.dump(metadata, f)
        logging.info(f"Saved run metadata to {meta_path.relative_to(save_path)}")

        # Save experiment parameters
        param_path = save_path / "00_experiment_parameters.yaml"
        with open(param_path, "w") as f:
            yaml.dump(experiment_parameters, f)
        logging.info(f"Saved experiment parameters to {param_path.relative_to(save_path)}")

        # Save run logs
        log_path = save_path / "00_run_logs.log"
        if log_path.exists():
            logging.info(f"Saved run logs to {log_path.relative_to(save_path)}")

        return metadata, experiment_parameters, log_path

    except Exception as e:
        logging.error(f"Failed to save run metadata, parameters & logs: {e}", exc_info=True)


def save_data(datasets: dict, save_path: pathlib.Path) -> None:
    """Saves datasets (DataFrames) to CSV in the specified path."""

    # Save each dataset
    for filename, data in datasets.items():
        
        if data is None:
            continue
            
        if data.empty:
            logging.warning(f"No data to save for {filename.split('/')[-1]}")
            continue

        # Create full path
        full_path = pathlib.Path(save_path / filename)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Save to CSV
        data.to_csv(full_path, index=False)
        logging.info(f"Saved {filename.split('/')[-1]} to {full_path.parent.relative_to(save_path)}")