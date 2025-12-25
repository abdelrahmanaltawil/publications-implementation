# env imports
import yaml
import pathlib

# local imports
import active_flow.steady_state_analysis.workflow as steady_state_analysis_workflow
import active_flow.extrema_search.workflow as extrema_search_workflow
import active_flow.hyperuniformity_analysis.workflow as hyperuniformity_analysis_workflow


def run(simulation_experiment_id: str) -> None:
    '''
    Placeholder
    '''

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