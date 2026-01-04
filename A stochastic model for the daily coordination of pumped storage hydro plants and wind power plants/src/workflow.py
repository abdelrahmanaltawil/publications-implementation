"""
EcoNex Workflow - Main Execution Script.

Orchestrates the full optimization pipeline:
1. Load configuration
2. Build network data (preprocessing)
3. Construct and solve Pyomo model (optimization)
4. Extract and save results (postprocessing)

All parameters are read from the config file - no CLI arguments needed.
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.helpers.logging_config import setup_logger
from src.preprocessing import load_config, build_network_data
from src.optimization import build_model, solve_model
from src.postprocessing import (
    extract_solution, save_results, log_metadata, print_summary,
    create_run_directory, save_config
)


def run(config_path: str = None):
    """
    Run the EcoNex optimization workflow.
    
    All parameters are read from the configuration file.
    
    Parameters
    ----------
    config_path : str, optional
        Path to configuration YAML file. If None, uses default path.
    
    Returns
    -------
    dict or None
        Solution dictionary if successful, None otherwise.
    """
    # Determine paths
    project_root = Path(__file__).parent.parent

    if config_path is None:
        config_path = project_root / 'data' / 'inputs' / 'config.yaml'
    else:
        config_path = Path(config_path)
    
    output_dir = project_root / 'data' / 'results'
    
    # Create run directory first (so we can log to it)
    run_dir = create_run_directory(str(output_dir))
    
    # Setup logging with log file in run directory
    log_file = run_dir / 'run.log'
    config_temp = load_config(str(config_path))
    
    # Get logging settings from config
    log_level_str = config_temp.get('logging', {}).get('level', 'INFO')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    logger = setup_logger("econex", level=log_level, log_file=str(log_file))
    
    logger.info("=" * 60)
    logger.info("EcoNex Resilient Micro-District Optimization")
    logger.info("=" * 60)
    logger.info(f"Run directory: {run_dir.relative_to(project_root)}")
    
    # Step 1: Load configuration
    logger.info("[1/4] Loading configuration...")
    try:
        config = load_config(str(config_path.relative_to(project_root)))
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        return None
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return None
    
    # Save config to run directory
    save_config(config, run_dir, str(config_path))
    
    # Step 2: Build network data
    logger.info("[2/4] Building network data...")
    data = build_network_data(config)
    logger.info(f"       Nodes: {data['nodes']}")
    logger.info(f"       Layers: {data['layers']}")
    logger.info(f"       Time steps: {len(data['T'])}")
    logger.info(f"       Arcs: {len(data['arcs'])}")
    
    # Step 3: Build and solve model
    logger.info("[3/4] Building and solving optimization model...")
    model = build_model(data)
    logger.info(f"       Model: {model.name}")
    
    # Get solver from config
    solver = config.get('solver', {}).get('name', 'glpk')
    verbose = config.get('solver', {}).get('verbose', False)
    
    try:
        model, results = solve_model(model, solver=solver, tee=verbose)
        logger.info(f"       Solver: {solver}")
        logger.info(f"       Status: {results.solver.termination_condition}")
    except RuntimeError as e:
        logger.error(f"Solver failed: {e}")
        logger.info(f"Install GLPK: brew install glpk (macOS) or apt-get install glpk-utils (Linux)")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during solving: {e}", exc_info=True)
        return None
    
    # Step 4: Extract and save results
    logger.info("[4/4] Extracting and saving results...")
    solution = extract_solution(model)
    
    save_results(solution, run_dir)
    log_metadata(model, results, run_dir)
    
    # Print summary
    print_summary(solution)
    
    logger.info(f"All outputs saved to: {run_dir}")
    logger.info("Workflow completed successfully")
    
    return solution


if __name__ == "__main__":
    # Simple execution - all parameters from config file
    run()
