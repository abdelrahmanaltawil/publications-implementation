# env imports
import pathlib
import yaml
import numpy as np


# def parse_parameters(parameters_path: pathlib.Path) -> None:
#     '''
#     Placeholder
#     '''

#     with open(parameters_path, "r") as file:
#         parameters = yaml.safe_load(file)

#     domain_length = parameters["algorithm"]["discretization"]["domain_length"]
    
#     if "pi" in domain_length:
#         domain_length.str        





def load_results() -> np.ndarray:
    '''
    Placeholder
    '''

    RESULTS_PATH = "./ratio_5"
    SAVE_PATH="./data/simulation"


    for file_path in pathlib.Path(RESULTS_PATH).glob("*.npz")[0::5]:
        snapshot = np.load(file_path)

        np.save(SAVE_PATH+file_path, snapshot["arr_0"])




with open(pathlib.Path("./parameters/simulation.yml"), "r") as file:
    parameters = yaml.safe_load(file)

    discretization = parameters["algorithm"]["discretization"]
    physical = parameters["algorithm"]["physical"]

    
print(discretization["domain_length"])
print(2*np.pi)
