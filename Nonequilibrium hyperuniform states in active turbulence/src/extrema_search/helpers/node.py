"""
Node class for grid-based extrema detection.

Provides a data structure representing a single point in the computational grid,
with neighbor relationships for identifying local minima and maxima.
"""

from dataclasses import dataclass
import numpy as np
from operator import attrgetter


class Node:
    """
    A grid point with position, value, and neighbor relationships.
    
    Used to represent points in a 2D vorticity field for extrema detection.
    Each node knows its 8 neighbors (if not on boundary) and can determine
    if it is a local minimum or maximum.
    
    Parameters
    ----------
    x : float
        x-coordinate in physical space.
    y : float
        y-coordinate in physical space.
    z : float
        Vorticity value ω(x, y) at this point.
    boundary : bool, optional
        Whether this node is on the domain boundary. Default False.
    
    Attributes
    ----------
    neighbors : list
        List of 8 neighboring Node objects (empty if boundary).
        Order: [upper, upper-right, right, lower-right, 
                lower, lower-left, left, upper-left]
    extrema : bool
        Flag indicating if this node is an extremum.
    """
    
    def __init__(self, x: float, y: float, z: float, boundary: bool =False) -> None:
        # function information
        self.x = x
        self.y = y
        self.z = z

        # neighbor "handeled when grid created"
        self.neighbors = []     # convetion [upper, right-upper, right, right-bottom, 
                                #            bottom, left-bottom, left, left-upper]
        
        self.extrema = False
        self.boundary = boundary


    def neighborhood_infromation(self):
        """
        Get coordinates of this node and its cardinal neighbors.
        
        Returns
        -------
        X : list
            x-coordinates [self, upper, right, lower, left].
        Y : list
            y-coordinates [self, upper, right, lower, left].
        Z : list
            z-values (vorticity) [self, upper, right, lower, left].
        """
        X = [self.x];  Y = [self.y]; Z = [self.z]
        for i in [0, 2, 4, 6]:
            X.append(self.neighbors[i].x)
            Y.append(self.neighbors[i].y)
            Z.append(self.neighbors[i].z)

        return X, Y, Z


    def is_extrema(self):
        """
        Check if this node is a local extremum.
        
        A node is an extremum if its z-value is either greater than
        all neighbors (local maximum) or less than all neighbors
        (local minimum).
        
        Returns
        -------
        bool
            True if this node is a local minimum or maximum.
        """
        min_node = min(self.neighbors, key=attrgetter('z'))
        max_node = max(self.neighbors, key=attrgetter('z'))
        return self < min_node or self > max_node


    def get_coord(self):
        """
        Get the position vector of this node.
        
        Returns
        -------
        np.ndarray
            Array [x, y, z] of node coordinates and value.
        """
        return np.array([self.x, self.y, self.z])


    def __lt__(self, other):
        """Compare nodes by z-value (less than)."""
        return self.z < other.z


    def __gt__(self, other):
        """Compare nodes by z-value (greater than)."""
        return self.z > other.z


    def __str__(self):
        """String representation showing (x, y, z) coordinates."""
        return '('+str(self.x)+', '+str(self.y)+', '+str(self.z)+')'

if __name__ == "__main__":
    node = Node(x=1, y=0, z=10)
    print(node)
