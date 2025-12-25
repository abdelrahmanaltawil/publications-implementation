"""
Global state registry for the extrema search module.

Provides a shared dictionary to pass data between preprocessing,
algorithm, and postprocessing stages without explicit parameter passing.
"""

# env imports
import numpy as np

# local imports

def init_register() -> None:
    """
    Initialize the global register dictionary.
    
    Creates a global `register` dictionary with pre-allocated keys
    for storing operators, snapshots, grids, and extrema data.
    
    Notes
    -----
    Keys initialized:
    - "operators": Spatial/frequency grids (x_vectors, k_vectors)
    - "snapshots": Vorticity snapshots in Fourier space
    - "grids": 2D arrays of Node objects
    - "grids_extrema": Detected extrema positions
    """

    global register

    register = {}

    # allocate keys values
    register["operators"] = None
    register["snapshots"] = None


    register["grids"] = None

    register["grids_extrema"] = None
