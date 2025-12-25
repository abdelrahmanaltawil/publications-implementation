# env imports
import logging
import zipfile
import pathlib 
import numpy as np
from re import search

# local imports
import hyperuniformity_analysis.helpers.register as re


def unzip_delete_file(file_path: pathlib.Path) -> None:
    """
    Extract a zip archive and delete the original zip file.
    
    Parameters
    ----------
    file_path : pathlib.Path
        Path to the zip file to extract.
    
    Notes
    -----
    Files are extracted to the current working directory.
    The original zip file is deleted after extraction.
    """

    # unzip
    with zipfile.ZipFile(file_path, 'r') as zip_file:
        zip_file.extractall(".")
        zip_file.close()

    # delete
    file_path.unlink()


def load_arrays(read_path: pathlib.Path, snapshots_locations: list[str]) -> tuple[dict]:
    """
    Load operator arrays and extrema snapshots from disk.
    
    Loads wavenumber operators and extrema positions for all extrema
    types (all_extrema, minima, maxima) at specified iteration locations.
    
    Parameters
    ----------
    read_path : pathlib.Path
        Directory containing the saved arrays and snapshots.
    snapshots_locations : list[str]
        List of iteration numbers to load (e.g., [10000, 20000, 30000]).
    
    Returns
    -------
    operators : dict
        Dictionary mapping operator names to numpy arrays.
        Contains 'k_vectors', 'x_vectors', etc.
    snapshots : dict
        Nested dictionary structure:
        {extrema_type: {iteration: extrema_positions}}
        where extrema_positions has shape (N, 3) with [x, y, z].
    
    Notes
    -----
    Results are also registered in re.register["operators"] and
    re.register["snapshots"] for access by other functions.
    """

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