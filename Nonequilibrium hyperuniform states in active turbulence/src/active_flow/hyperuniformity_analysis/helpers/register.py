# env imports
import numpy as np

# local imports

def init_register() -> None:
    '''
    Placeholder
    '''

    global register

    register = {}

    # allocate keys values
    register["operators"] = None
    register["snapshots"] = None

    register["snapshots_density"] = None
    register["snapshots_structure_factor"] = None
    register["snapshots_radial_profile"] = None

