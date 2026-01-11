# env imports
import pathlib
import yaml
import numpy as np


def load_results() -> np.ndarray:
    """
    Load simulation results from npz files (Legacy/Script).

    This function appears to be a helper for converting or moving
    specific .npz snapshot files to a new directory.

    Returns
    -------
    np.ndarray
        The last loaded snapshot array.
    """

    RESULTS_PATH = "./ratio_5"
    SAVE_PATH="./data/simulation"


    for file_path in pathlib.Path(RESULTS_PATH).glob("*.npz")[0::5]:
        snapshot = np.load(file_path)

        np.save(SAVE_PATH+file_path, snapshot["arr_0"])
        
    return snapshot["arr_0"]


if __name__ == "__main__":
    with open(pathlib.Path("./parameters/simulation.yml"), "r") as file:
        parameters = yaml.safe_load(file)

    discretization = parameters["algorithm"]["discretization"]
    physical = parameters["algorithm"]["physical"]

    
    print(discretization["domain_length"])
    print(2*np.pi)
