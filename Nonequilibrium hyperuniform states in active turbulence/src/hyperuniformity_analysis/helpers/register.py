"""
Global state registry for the hyperuniformity analysis module.

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
    for storing operators, snapshots, and computed quantities.
    
    Notes
    -----
    Keys initialized:
    - "operators": Spatial/frequency grids (x_vectors, k_vectors)
    - "snapshots": Extrema positions by type
    - "snapshots_density": Fourier density ñ(k)
    - "snapshots_structure_factor": 2D S(kx, ky)
    - "snapshots_radial_profile": 1D S(|k|)
    """

    global register

    register = {}

    # allocate keys values
    register["operators"] = None
    register["snapshots"] = None

    register["snapshots_density"] = None
    register["snapshots_structure_factor"] = None
    register["snapshots_radial_profile"] = None
