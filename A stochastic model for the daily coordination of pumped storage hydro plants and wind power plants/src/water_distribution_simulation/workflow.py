"""Water Distribution Simulation Workflow - Main Execution Script.

Orchestrates the full simulation pipeline:
1. Load configuration
2. Preprocess network (load, configure demands, controls)
3. Run WNTR simulation
4. Extract and save results (postprocessing)

All parameters are read from the config file - no CLI arguments needed.
"""

import logging
import sys
import warnings
from pathlib import Path


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.helpers.logging_config import setup_logger
import src.water_distribution_simulation.preprocessing as preprocessing
import src.water_distribution_simulation.algorithm_tasks as algorithm
import src.water_distribution_simulation.postprocessing as postprocessing


if __name__ == "__main__":

    # Determine paths
    project_root = Path(__file__).resolve().parents[2]
    config_path = (project_root / 'data' / 'inputs' / 'config'
                            / 'water_distribution_simulation' / 'config.yaml')
    
    # Load config to get output directory
    config = preprocessing.load_config(str(config_path))
    output_dir = project_root / config['paths']['output_dir']
    
    # Preprocessing
    run_dir = preprocessing.create_run_directory(str(output_dir))
    
    # Setup logging
    log_file = run_dir / 'metadata' / 'run.log'
    logger = setup_logger("wds", log_file=str(log_file))

    logger.info("Water Distribution Simulation (WNTR)")
    logger.info(f"Run directory: {run_dir}")
    
    # Step 1: Preprocess
    logger.info("[1/4] Loading configuration and preprocessing network...")
    
    try:
        wn = preprocessing.load_network(config['network']['inp_file'])   
    except Exception as e:
        logger.error(f"Preprocessing failed: {e}", exc_info=True)
        sys.exit(1)

    
    logger.info(f"Network: {wn.num_nodes} nodes, {wn.num_links} links")
    logger.info(f"Duration: {wn.options.time.duration / 3600:.1f} hours")
    logger.info(f"Hydraulic Timestep: {wn.options.time.hydraulic_timestep / 60:.1f} minutes")

    
    # Algorithm tasks
    # Step 2: Run simulation
    logger.info("[2/4] Running hydraulic simulation...")
    simulator = config.get('simulation', {}).get('simulator', 'wntr')
    
    try:
        results = algorithm.run_simulation(wn, simulator_type=simulator)
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        sys.exit(1)

    # Postprocessing
    # Step 3: Extract results
    logger.info("[3/4] Extracting results...")
    extracted = postprocessing.extract_results(results, wn)
    
    # Step 4: Compute summary and save results
    logger.info("[4/4] Computing metrics and saving results...")
    summary = postprocessing.create_summary(run_dir.name, results, wn)
    postprocessing.save_results(extracted, summary, run_dir)
    postprocessing.save_config(run_dir, str(config_path))
    preprocessing.save_inp_file(config, run_dir)
    postprocessing.log_metadata(run_dir)
    
    logger.info(f"All outputs saved to: {run_dir}")
    logger.info("Workflow completed successfully")
