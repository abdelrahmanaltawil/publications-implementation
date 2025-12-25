# env imports
import yaml
import pathlib

# local imports
import steady_state_analysis.workflow as steady_state_analysis_workflow
import extrema_search.workflow as extrema_search_workflow
import hyperuniformity_analysis.workflow as hyperuniformity_analysis_workflow


def run(simulation_experiment_id: str) -> None:
    """
    Run the complete analysis pipeline for a simulation experiment.
    
    Executes the three post-simulation analysis stages in sequence:
    1. Steady State Analysis - Identifies equilibrated snapshots
    2. Extrema Search - Finds vortex centers (minima/maxima)
    3. Hyperuniformity Analysis - Computes structure factor S(k)
    
    Each stage reads from the previous stage's Neptune.ai run and 
    creates a new run with its results.
    
    Parameters
    ----------
    simulation_experiment_id : str
        Neptune.ai run ID from a completed simulation (e.g., "AC-895").
        This is used as the starting point for the analysis chain.
    
    Returns
    -------
    None
        All results are uploaded to Neptune.ai.
    
    Example
    -------
    >>> run(simulation_experiment_id="AC-895")
    # Runs: Steady State → Extrema Search → Hyperuniformity
    """

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

    run(
        simulation_experiment_id= "AC-895"
        )