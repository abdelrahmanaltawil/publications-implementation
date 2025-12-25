"""
Global state registry for the steady-state analysis module.

Provides a shared dictionary to pass data between preprocessing,
algorithm, and postprocessing stages without explicit parameter passing.
"""


def init_register() -> None:
    """
    Initialize the global register dictionary.
    
    Creates a global `register` dictionary with pre-allocated keys
    for storing operators and snapshots.
    
    Notes
    -----
    Keys initialized:
    - "operators": Spatial/frequency grids (x_vectors, k_vectors)
    - "snapshots": Vorticity snapshots at selected iterations
    """

    global register
    register = {}

    # allocate keys values
    register["operators"] = {}
    register["snapshots"] = {}    
