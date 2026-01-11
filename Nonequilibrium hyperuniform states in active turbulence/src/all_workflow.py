# env imports
import yaml
import pathlib
import sys

# Ensure project level imports
sys.path.append(str(pathlib.Path(__file__).parent))

# local imports
import simulation.workflow as simulation_workflow
import steady_state_analysis.workflow as steady_state_analysis_workflow
import extrema_search.workflow as extrema_search_workflow
import hyperuniformity_analysis.workflow as hyperuniformity_analysis_workflow


def run(simulation_parameters: dict) -> None:
    """
    Run the complete simulation + analysis pipeline.
    
    Executes the simulation and the three post-simulation analysis stages in sequence:
    1. Simulation - Runs the active flow simulation
    2. Steady State Analysis - Identifies equilibrated snapshots
    3. Extrema Search - Finds vortex centers (minima/maxima)
    4. Hyperuniformity Analysis - Computes structure factor S(k)
    
    Each stage reads from the previous stage's Neptune.ai run and 
    creates a new run with its results.
    
    Parameters
    ----------
    simulation_parameters : dict
        Configuration dictionary from simulation.yml containing:
        - algorithm.discretization: Grid and time-stepping parameters
        - algorithm.physical: PVC model parameters
        - preprocessing: Seed and monitoring settings
        - postprocessing: Save path and quantities to save
    
    Returns
    -------
    None
        All results are uploaded to Neptune.ai.
    
    Example
    -------
    >>> run(simulation_parameters=simulation_parameters)
    # Runs: Simulation → Steady State → Extrema Search → Hyperuniformity
    """

    simulation_experiment_id = simulation_workflow.run(
        parameters= simulation_parameters
        )

    with open(pathlib.Path("./parameters/steady_state_analysis.yml"), "r") as file:
        parameters = yaml.safe_load(file)
        parameters["preprocessing"]["experiment_ID"] = simulation_experiment_id

    steady_state_run_id = steady_state_analysis_workflow.run(
        parameters= parameters
        )


    with open(pathlib.Path("./parameters/extrema_search.yml"), "r") as file:
        parameters = yaml.safe_load(file)
        parameters["preprocessing"]["experiment_ID"] = steady_state_run_id

    extrema_search_run_id = extrema_search_workflow.run(
        parameters= parameters
        )


    with open(pathlib.Path("./parameters/hyperuniformity_analysis.yml"), "r") as file:
        parameters = yaml.safe_load(file)
        parameters["preprocessing"]["experiment_ID"] = extrema_search_run_id

    hyperuniformity_analysis_workflow.run(
        parameters= parameters
        )


if __name__ == "__main__":

    with open(pathlib.Path("./parameters/simulation.yml"), "r") as file:
        simulation_parameters = yaml.safe_load(file)

    run(
        simulation_parameters= simulation_parameters
        )