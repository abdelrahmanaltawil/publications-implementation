# env imports 
import numpy as np
import pandas as pd
import scipy.fftpack as scipy
from operator import attrgetter


# local imports 
import active_flow.extrema_search.helpers.node as nd
import active_flow.extrema_search.helpers.register as re


def compute_vorticity(snapshots: dict) -> dict:
    '''
    Placeholder
    '''

    w_snapshots={}
    for key, value in snapshots.items():
        w_snapshots[key] = np.real(scipy.ifft2(value))
    
    # register
    re.register["snapshots"] = w_snapshots

    return w_snapshots


def create_grid(x: np.ndarray, y: np.ndarray, w: dict) -> dict:
    '''
    fill grid with Node objects 
    '''

    grids={}
    for key, value in w.items():
        # nodes = np.empty((len(x), len(y[0])), dtype=object)

        # # optimization is not the goal here
        # for i in range(len(x)):
        #     for j in range(len(y[0])):
        #         bool = at_boundary(i, j, len(x)-1)
        #         nodes[i, j] = nd.Node(x[i,j], y[i,j], value[i,j], boundary=bool)

        # for i, row in enumerate(nodes):
        #     for j, node in enumerate(row):
        #         find_neighbors(node, nodes, i, j) # this can take i and j

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
    '''
    Placeholder
    '''

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
    '''
    find the close neighbors of node in the grid
    '''

    if node.boundary:
        return

    for neighbor in [(i-1, j), (i-1,j+1), (i, j+1), (i+1,j+1), 
                        (i+1,j), (i+1,j-1), (i,j-1), (i-1,j-1)]:
        node.neighbors.append(nodes[neighbor])
    

def find_extrema(grids: dict, threshold=None) -> dict[dict]:
    '''
    threshold   :   float
                    define lower bound on the allowable extrema "by absolute value"
    '''
    
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
    '''
    Placeholder
    '''

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
    '''
        x : float
            node x coordinate
        y : float
            node y coordinate
    '''

    if i in [0, end] or j in [0, end]:
        return True
    return False
