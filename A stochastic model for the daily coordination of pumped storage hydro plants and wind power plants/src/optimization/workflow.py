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
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.helpers.logging_config import setup_logger
import src.optimization.preprocessing as preprocessing
import src.optimization.algorithm_tasks as algorithm
import src.optimization.postprocessing as postprocessing


if __name__ == "__main__":

    # Determine paths
    project_root = Path(__file__).parents[2]
    config_path = project_root / 'data' / 'inputs' / 'config' / 'optimization' /  'config.yaml'
    
    # Load config to get output directory
    config = preprocessing.load_config(str(config_path))
    output_dir = project_root / config['paths']['output_dir']

    # Preprocessing
    run_dir = preprocessing.create_run_directory(str(output_dir))
    
    # Setup logging
    log_file = run_dir / 'metadata' / 'run.log'
    logger = setup_logger("econex", log_file=str(log_file))

    logger.info("EcoNex Resilient Micro-District Optimization")
    logger.info(f"Run directory: {run_dir}")
    
    # Step 1: Load configuration
    logger.info("[1/4] Loading configuration...")
    config = preprocessing.load_config(str(config_path))
    
    # Step 2: Build network data
    logger.info("[2/4] Building network data...")
    data = preprocessing.build_network_data(config)
    
    # algorithm tasks
    # Step 3: Build and solve model
    logger.info("[3/4] Building and solving optimization model...")
    model = algorithm.build_model(data)
    
    solver_results = None
    try:
        model, solver_results = algorithm.solve_model(model, 
                                        solver=config['solver']['name'], 
                                        tee=config['solver']['verbose'],
                                        logfile=str(run_dir / 'metadata' / 'solver.log')
                                    )
    except RuntimeError as e:
        logger.error(f"Solver failed: {e}")
        logger.info(f"Install GLPK: brew install glpk (macOS) or apt-get install glpk-utils (Linux)")
    except Exception as e:
        logger.error(f"Unexpected error during solving: {e}", exc_info=True)
    
    # Step 3: Extract solution
    logger.info("Extracting solution...")
    # Solve model
    solution = postprocessing.extract_solution(model)
    
    if solver_results:
        summary = postprocessing.create_summary(run_dir.name, model, solution, solver_results)
    else:
        logger.warning("No solver results. Generating partial summary.")
        summary = {
            'run_id': run_dir.name, 
            'solver_status': 'Failed', 
            'termination_condition': 'Error',
            'objective_value': solution.get('objective')
        }
    
    # Step 4: Save results
    logger.info("Saving results...")
    postprocessing.save_results(solution, summary, run_dir)
    postprocessing.save_config(run_dir, str(config_path))
    postprocessing.save_inp_file(run_dir, config['inp_file'])
    postprocessing.log_metadata(run_dir)
    
    logger.info(f"Optimization completed. Results in {run_dir}")
    logger.info("Workflow completed successfully")
