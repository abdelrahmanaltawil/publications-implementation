"""EcoNex Workflow — single entry point.

Orchestrates the full pipeline:
  1. Build network data (water + energy as configured)
  2. Build and solve the Pyomo model
  3. Extract and save results

All parameters are read from data/inputs/config.yaml — no CLI arguments needed.
Set config flags to control what is built:
  run_water: true   → run water sub-model (W1–W24)
  run_energy: false → run energy sub-model (E1–E13)   [default: false until implemented]
  run_nexus: false  → run coupled model               [default: false until nexus is built]
"""

# imports
import json
import logging
import os
import sys
import datetime
import platform
import socket
import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# local imports
from src import preprocessing, algorithm_tasks as algorithm, postprocessing
from src.helpers.utils import load_config, save_config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] \033[1m%(module)s\033[0m - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


def setup_run_logging(save_path: Path) -> None:
    """Configures the file handler to save logs to the run directory."""

    log_path = save_path / "metadata" / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(module)s - %(message)s"))
    logging.getLogger().addHandler(file_handler)
    logging.info(f"Experiment results will be saved to: {save_path}")


def collect_run_metadata(save_path: Path) -> dict:
    """Collects run environment and versioning details."""

    metadata = {
        "experiment_id": save_path.name,
        "execution_start_time": datetime.datetime.now().isoformat(),
        "timestamp": datetime.datetime.now().isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "user": getpass.getuser(),
        "hostname": socket.gethostname(),
        "working_directory": os.getcwd(),
        "command": " ".join(sys.argv),
    }

    logging.info("Collecting run environment and versioning details...")
    logging.info(f"Experiment ID: {metadata['experiment_id']} (started at {metadata['execution_start_time']})\n")

    return metadata


if __name__ == "__main__":

    project_root = Path(__file__).parents[1]

    # load configuration
    config = load_config(str(project_root / "data" / "inputs" / "config.yaml"))

    # preprocessing
    output_dir = project_root / config["paths"]["output_dir"]
    run_dir = preprocessing.create_run_directory(str(output_dir))

    # logging and metadata collection
    setup_run_logging(save_path=run_dir)
    metadata = collect_run_metadata(save_path=run_dir)

    # build network data
    logging.info("[1/3] Building network data...")
    try:
        data = preprocessing.build_network_data(config, project_root)
    except FileNotFoundError as e:
        logging.error(f"Network file missing: {e}")
        sys.exit(1)

    # build and solve model
    logging.info("[2/3] Building and solving optimization model...")
    model = algorithm.build_model(data, config)

    solver_cfg = config.get("solver", {})
    solver_results = None
    try:
        model, solver_results = algorithm.solve_model(
            model,
            solver=solver_cfg.get("name", "glpk"),
            tee=solver_cfg.get("verbose", True),
            timeout=solver_cfg.get("timeout", 300),
            logfile=str(run_dir / "metadata" / "solver.log"),
        )
    except RuntimeError as e:
        logging.error(f"Solver failed: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during solving: {e}", exc_info=True)

    # postprocessing
    logging.info("[3/3] Saving results...")
    solution = postprocessing.extract_solution(model)

    if solver_results:
        summary = postprocessing.create_summary(run_dir.name, model, solution, solver_results)
    else:
        summary = {"run_id": run_dir.name, "solver_status": "Failed",
                   "objective_value": solution.get("objective")}

    postprocessing.save_results(solution, summary, run_dir)
    postprocessing.save_network_files(run_dir, config, project_root)
    save_config(run_dir, str(project_root / "data" / "inputs" / "config.yaml"))

    # finalize metadata and save
    metadata["execution_end_time"] = datetime.datetime.now().isoformat()
    start = datetime.datetime.fromisoformat(metadata["execution_start_time"])
    metadata["execution_duration_min"] = round((datetime.datetime.now() - start).total_seconds() / 60, 3)

    meta_path = run_dir / "metadata" / "run_metadata.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logging.info(f"Pipeline completed successfully. Elapsed time: {metadata['execution_duration_min']:.2f} min. Results in: {run_dir}")
