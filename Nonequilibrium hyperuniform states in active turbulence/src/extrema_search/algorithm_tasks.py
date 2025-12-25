# env imports 
import numpy as np
import pandas as pd
import scipy.fftpack as scipy
from operator import attrgetter


# local imports 
import extrema_search.helpers.node as nd
import extrema_search.helpers.register as re


def compute_vorticity(snapshots: dict) -> dict:
    """
    Transform vorticity snapshots from Fourier space to physical space.
    
    Applies inverse 2D FFT to each snapshot to obtain the real-space 
    vorticity field ω(x, y) from the Fourier coefficients ω̂(kx, ky).
    
    Parameters
    ----------
    snapshots : dict
        Dictionary mapping snapshot names to vorticity arrays in Fourier space.
        Each value should be a 2D complex numpy array.
    
    Returns
    -------
    dict
        Dictionary with same keys, containing real-space vorticity fields.
        Also registered in re.register["snapshots"].
    """

    w_snapshots={}
    for key, value in snapshots.items():
        w_snapshots[key] = np.real(scipy.ifft2(value))
    
    # register
    re.register["snapshots"] = w_snapshots

    return w_snapshots


def create_grid(x: np.ndarray, y: np.ndarray, w: dict) -> dict:
    """
    Create a grid of Node objects from coordinate and vorticity data.
    
    Constructs a 2D grid where each point is a Node object containing
    position (x, y), vorticity value (z), and references to neighboring nodes.
    
    Parameters
    ----------
    x : np.ndarray
        2D array of x-coordinates, shape (N, N).
    y : np.ndarray
        2D array of y-coordinates, shape (N, N).
    w : dict
        Dictionary mapping snapshot names to vorticity fields.
    
    Returns
    -------
    dict
        Dictionary mapping snapshot names to 2D arrays of Node objects.
        Also registered in re.register["grids"].
    """

    grids={}
    for key, value in w.items():
        nodes = _create_grid(
            x= x,
            y= y,
            w= value
        )

        grids[key] = nodes

    # register
    re.register["grids"] = grids

    return grids


def _create_grid(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> np.ndarray:
    """
    Internal function to create a single grid of Node objects.
    
    Creates Node objects for each grid point, marks boundary nodes,
    and establishes neighbor relationships for interior nodes.
    
    Parameters
    ----------
    x : np.ndarray
        2D array of x-coordinates.
    y : np.ndarray
        2D array of y-coordinates.
    w : np.ndarray
        2D array of vorticity values.
    
    Returns
    -------
    np.ndarray
        2D array of Node objects with neighbor relationships established.
    """

    nodes = np.empty((len(x), len(y[0])), dtype=object)

    # optimization is not the goal here
    for i in range(len(x)):
        for j in range(len(y[0])):
            bool = at_boundary(i, j, len(x)-1)
            nodes[i, j] = nd.Node(x[i,j], y[i,j], w[i,j], boundary=bool)

    for i, row in enumerate(nodes):
        for j, node in enumerate(row):
            find_neighbors(node, nodes, i, j) # this can take i and j

    return nodes


def find_neighbors(node, nodes, i, j):
    """
    Find and assign the 8 nearest neighbors of a grid node.
    
    For interior nodes (not on boundary), identifies all 8 adjacent
    nodes in the grid and adds them to the node's neighbors list.
    
    Parameters
    ----------
    node : Node
        The node for which to find neighbors.
    nodes : np.ndarray
        2D array of all Node objects in the grid.
    i : int
        Row index of the node in the grid.
    j : int
        Column index of the node in the grid.
    
    Notes
    -----
    Boundary nodes are skipped as they have incomplete neighborhoods.
    """

    if node.boundary:
        return

    for neighbor in [(i-1, j), (i-1,j+1), (i, j+1), (i+1,j+1), 
                        (i+1,j), (i+1,j-1), (i,j-1), (i-1,j-1)]:
        node.neighbors.append(nodes[neighbor])
    

def find_extrema(grids: dict, threshold=None) -> dict[dict]:
    """
    Find local extrema (minima and maxima) in vorticity field snapshots.
    
    Identifies vortex centers by finding points where the vorticity
    is a local minimum or maximum compared to all 8 neighbors.
    
    Parameters
    ----------
    grids : dict
        Dictionary mapping snapshot names to 2D arrays of Node objects.
    threshold : float, optional
        Minimum absolute vorticity value for an extremum to be included.
        Useful for filtering out weak/noise extrema. Default is None.
    
    Returns
    -------
    dict[dict]
        Nested dictionary structure:
        {iteration: {"All Extrema": array, "Minima": array, "Maxima": array}}
        Each array has shape (N, 3) with columns [x, y, vorticity].
    """
    
    grids_extrema=[]
    snapshots_extrema={}
    for key, grid_value in grids.items():
        all_extrema, minima, maxima = _find_extrema(
            grid= grid_value,
            threshold= threshold
            )

        iteration = key.replace("w_k_","").replace(".npy","").lstrip('0')
        iteration = "0" if iteration == "" else iteration
        iteration = "Iteration = " + iteration

        snapshots_extrema[iteration] = {
            "All Extrema": all_extrema,
            "Minima": minima,
            "Maxima": maxima
        }

    # register
    re.register["grids_extrema"] = grids_extrema

    return snapshots_extrema


def _find_extrema(grid: np.ndarray[nd.Node], threshold=None) -> tuple[np.ndarray]:
    """
    Internal function to find extrema in a single grid.
    
    Scans all nodes and identifies those that are local extrema
    (value greater or less than all 8 neighbors).
    
    Parameters
    ----------
    grid : np.ndarray[Node]
        2D array of Node objects.
    threshold : float, optional
        Minimum absolute vorticity for inclusion.
    
    Returns
    -------
    tuple[np.ndarray]
        Three arrays: (all_extrema, minima, maxima).
        Each array has shape (N, 3) with columns [x, y, z].
    """

    all_extrema= []
    minima=[]
    maxima=[]
    for node in grid.flatten():
        if not node.neighbors:
            continue

        if not node.is_extrema():
            continue

        if threshold != None:
            if np.abs(node.z) < threshold:
                continue

        all_extrema.append(np.array([node.x, node.y, node.z]))
        if node.z < min(node.neighbors, key=attrgetter('z')).z:
            minima.append(np.array([node.x, node.y, node.z]))
        else:
            maxima.append(np.array([node.x, node.y, node.z]))

    return np.array(all_extrema), np.array(minima), np.array(maxima)


def at_boundary(i, j, end):
    """
    Check if a grid index is on the boundary of the domain.
    
    Parameters
    ----------
    i : int
        Row index.
    j : int
        Column index.
    end : int
        Maximum valid index (grid size - 1).
    
    Returns
    -------
    bool
        True if the point is on any edge of the grid.
    """

    if i in [0, end] or j in [0, end]:
        return True
    return False
