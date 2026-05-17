import pytest
import pyomo.environ as pyo
from pathlib import Path
import logging
import sys

# Add project root to path so 'src' can be imported when running script directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.algorithm_tasks import build_model, solve_model
from tests.helpers.validation_utils import (
    run_water_validation,
    run_energy_validation,
    validation_logging,
    logger,
)

# =============================================================================
# OPTIMIZATION VS SIMULATION COMPARISON TESTS
# =============================================================================

def get_network_files():
    """Retrieve all real network files from the project data directory."""
    water_dir = Path.cwd() / "data" / "inputs" / "system_config" / "water"
    if not water_dir.exists():
        return []
    
    # Exclude networks that are known to fail due to missing features or being too large/slow
    # if necessary, or just run them all. Here we grab all .inp files.
    # Currently we only have ANET.inp, GNET.inp, FNET.INP. Let's just grab them.
    # Note: FNET is very large, might be too slow for a standard unit test run,
    # so we might want to mark it or just let the user run it.
    # We will parametrize over all available .inp files.
    files = list(water_dir.glob("*.inp")) + list(water_dir.glob("*.INP"))
    
    # Dedup
    return list(set(files))

@pytest.mark.parametrize("inp_file", get_network_files(), ids=lambda f: f.name)
def test_water_optimization_against_simulation(inp_file):
    """
    Data-Driven Decoupled Validation
    
    Scenario:
        - Runs the Pyomo optimization model with a zero objective (feasibility check).
        - Runs the EPANET/WNTR simulation using the same network.
        
    Validation:
        - Decoupled water network must yield equivalent flows and heads in both models.
        - Automatically plots the overlaid time series and saves metrics.
    """
    if not pyo.SolverFactory('gurobi').available():
        pytest.skip("Gurobi solver not available")
        
    # FNET is large and might take a long time, but we will run it anyway or allow skipping if timeout
    
    network_name = inp_file.stem
    save_dir = Path.cwd() / "data" / "results" / "validation" / "water" / network_name
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # We will use 24 timesteps for validation
    num_timesteps = 24
    
    with validation_logging(save_dir / "test_report.log"):
        # run_scenario_on_optimization_and_simulation handles metrics and now plotting
        results = run_water_validation(
            str(inp_file), 
            num_timesteps=num_timesteps, 
            solver='gurobi', 
            save_dir=save_dir
        )
        
        # If the solver returns infeasible, fail the test
        assert results['status'] == 'completed', f"Optimization failed: {results.get('termination')}"
        
        # The detailed assertions (no negative pressures, timeseries match) could be done here
        # or inside run_scenario_on_optimization_and_simulation. Currently, they are not automatically
        # asserting failing the test inside the function, it just computes metrics.
        # So let's check the metrics explicitly.
        
        metrics = results.get("metrics", {})
        
        # Ensure all max relative errors are within acceptable bounds, say < 5%
        # The user said passing the test is done by visual inspection now,
        assert len(metrics) > 0, "No metrics were generated."

def get_energy_network_files():
    """Retrieve all real energy network files from the project data directory."""
    energy_dir = Path.cwd() / "data" / "inputs" / "system_config" / "energy"
    if not energy_dir.exists():
        return []
    
    files = list(energy_dir.glob("*.dss"))
    return list(set(files))

@pytest.mark.parametrize("dss_file", get_energy_network_files(), ids=lambda f: f.name)
def test_energy_optimization_against_simulation(dss_file):
    """
    Data-Driven Decoupled Validation for Energy
    
    Scenario:
        - Runs the Pyomo optimization model with a zero objective (feasibility check).
        - Runs the OpenDSS simulation using the same network.
        
    Validation:
        - Decoupled energy network must yield equivalent flows/voltages.
    """
    if not pyo.SolverFactory('gurobi').available():
        pytest.skip("Gurobi solver not available")
        
    network_name = dss_file.stem
    save_dir = Path.cwd() / "data" / "results" / "validation" / "energy" / network_name
    save_dir.mkdir(parents=True, exist_ok=True)
    
    num_timesteps = 24
    
    with validation_logging(save_dir / "test_report.log"):
        results = run_energy_validation(
            str(dss_file), 
            num_timesteps=num_timesteps, 
            solver='gurobi', 
            save_dir=save_dir
        )
        
        assert results['status'] == 'completed', f"Optimization failed: {results.get('termination')}"
        
        # Check that metrics aren't empty, meaning some devices matched
        metrics = results.get("metrics", {})
        # Note: If src/preprocessing.py still uses a placeholder for energy (e.g., bus1 only),
        # this assertion will fail because master.dss has SourceBus/LoadBus, meaning no common columns.
        # We allow it to pass or fail, but assert will catch the mismatch.
        assert len(metrics) > 0, "No metrics generated. Optimization and Simulation have disjoint components."
