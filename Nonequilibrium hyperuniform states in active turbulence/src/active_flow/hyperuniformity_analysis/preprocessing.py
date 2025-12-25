# env imports
import logging
import zipfile
import pathlib 
import numpy as np
from re import search

# local imports
import active_flow.hyperuniformity_analysis.helpers.register as re


def unzip_delete_file(file_path: pathlib.Path) -> None:
    '''
    Placeholder
    '''

    # unzip
    with zipfile.ZipFile(file_path, 'r') as zip_file:
        zip_file.extractall(".")
        zip_file.close()

    # delete
    file_path.unlink()


def load_arrays(read_path: pathlib.Path, snapshots_locations: list[str]) -> tuple[dict]:
    '''
    Placeholder
    '''

    operators={}
    for path in read_path.glob("*.npy"):
        operators[path.stem] = np.load(path)
    
    snapshots={}
    for extrema_type in ["all_extrema", "minima", "maxima"]:

        extrema_type_snapshots={}
        for location in snapshots_locations:
            file_name = extrema_type+"_"+str(location).zfill(8)+".npy"
            extrema_path = read_path.joinpath("snapshots/extrema/"+file_name)

            try:
                extrema = np.load(extrema_path)
            except OSError:
                logging.warning("file "+str(extrema_path)+" could not be loaded.")
                continue
            
            key = "Iteration = " + str(location)
            extrema_type_snapshots[key] = extrema
        
        snapshots[extrema_type] = extrema_type_snapshots

    # register
    re.register["operators"] = operators
    re.register["snapshots"] = snapshots

    return operators, snapshots