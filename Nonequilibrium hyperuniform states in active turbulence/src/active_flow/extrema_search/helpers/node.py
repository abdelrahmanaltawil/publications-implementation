from dataclasses import dataclass
import numpy as np
from operator import attrgetter



class Node:
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
        X = [self.x];  Y = [self.y]; Z = [self.z]
        for i in [0, 2, 4, 6]:
            X.append(self.neighbors[i].x)
            Y.append(self.neighbors[i].y)
            Z.append(self.neighbors[i].z)

        return X, Y, Z


    def is_extrema(self):
        min_node = min(self.neighbors, key=attrgetter('z'))
        max_node = max(self.neighbors, key=attrgetter('z'))
        return self < min_node or self > max_node


    def get_coord(self):
        return np.array([self.x, self.y, self.z])


    def __lt__(self, other):
        return self.z < other.z


    def __gt__(self, other):
        return self.z > other.z


    def __str__(self):
        return '('+str(self.x)+', '+str(self.y)+', '+str(self.z)+')'

if __name__ == "__main__":
    node = Node(x=1, y=0, z=10)
    print(node)
