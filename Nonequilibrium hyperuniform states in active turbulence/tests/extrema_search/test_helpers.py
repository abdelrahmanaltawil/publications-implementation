"""
Tests for extrema_search/helpers/node.py

Tests cover the Node class, extrema detection, and comparison operators.
"""

import pytest
import numpy as np

from extrema_search.helpers.node import Node


class TestNodeInit:
    """Tests for Node initialization."""
    
    def test_coordinates_stored(self):
        """Node should store x, y, z correctly."""
        node = Node(x=1.0, y=2.0, z=3.0)
        
        assert node.x == 1.0
        assert node.y == 2.0
        assert node.z == 3.0
    
    def test_boundary_default_false(self):
        """boundary should default to False."""
        node = Node(x=1.0, y=2.0, z=3.0)
        
        assert node.boundary == False
    
    def test_boundary_can_be_set(self):
        """boundary can be set to True."""
        node = Node(x=1.0, y=2.0, z=3.0, boundary=True)
        
        assert node.boundary == True
    
    def test_neighbors_initially_empty(self):
        """neighbors list should start empty."""
        node = Node(x=1.0, y=2.0, z=3.0)
        
        assert node.neighbors == []
    
    def test_extrema_initially_false(self):
        """extrema flag should start False."""
        node = Node(x=1.0, y=2.0, z=3.0)
        
        assert node.extrema == False


class TestNodeIsExtrema:
    """Tests for the is_extrema method."""
    
    def _create_node_with_neighbors(self, center_z, neighbor_zs):
        """Helper to create a node with specified neighbor z-values."""
        center = Node(x=0, y=0, z=center_z)
        for i, z in enumerate(neighbor_zs):
            neighbor = Node(x=i*0.1, y=i*0.1, z=z)
            center.neighbors.append(neighbor)
        return center
    
    def test_local_maximum(self):
        """Node higher than all neighbors is maximum."""
        node = self._create_node_with_neighbors(
            center_z=10.0,
            neighbor_zs=[5.0, 6.0, 7.0, 8.0, 9.0, 4.0, 3.0, 2.0]
        )
        
        assert node.is_extrema() == True
    
    def test_local_minimum(self):
        """Node lower than all neighbors is minimum."""
        node = self._create_node_with_neighbors(
            center_z=-10.0,
            neighbor_zs=[5.0, 6.0, 7.0, 8.0, 9.0, 4.0, 3.0, 2.0]
        )
        
        assert node.is_extrema() == True
    
    def test_saddle_point(self):
        """Node between max and min neighbors is not extremum."""
        node = self._create_node_with_neighbors(
            center_z=5.0,
            neighbor_zs=[1.0, 2.0, 3.0, 7.0, 8.0, 9.0, 4.0, 6.0]
        )
        
        assert node.is_extrema() == False


class TestNodeGetCoord:
    """Tests for the get_coord method."""
    
    def test_returns_array(self):
        """get_coord should return numpy array."""
        node = Node(x=1.0, y=2.0, z=3.0)
        
        coord = node.get_coord()
        
        assert isinstance(coord, np.ndarray)
    
    def test_correct_values(self):
        """Array should contain [x, y, z]."""
        node = Node(x=1.5, y=2.5, z=3.5)
        
        coord = node.get_coord()
        
        np.testing.assert_array_equal(coord, [1.5, 2.5, 3.5])


class TestNodeComparison:
    """Tests for comparison operators."""
    
    def test_less_than(self):
        """< should compare z values."""
        node1 = Node(x=0, y=0, z=1.0)
        node2 = Node(x=0, y=0, z=2.0)
        
        assert (node1 < node2) == True
        assert (node2 < node1) == False
    
    def test_greater_than(self):
        """> should compare z values."""
        node1 = Node(x=0, y=0, z=1.0)
        node2 = Node(x=0, y=0, z=2.0)
        
        assert (node2 > node1) == True
        assert (node1 > node2) == False
    
    def test_equal_z_values(self):
        """Equal z values: neither < nor >."""
        node1 = Node(x=0, y=0, z=5.0)
        node2 = Node(x=1, y=1, z=5.0)
        
        assert (node1 < node2) == False
        assert (node1 > node2) == False


class TestNodeStr:
    """Tests for string representation."""
    
    def test_str_format(self):
        """__str__ should return (x, y, z) format."""
        node = Node(x=1, y=2, z=3)
        
        s = str(node)
        
        assert s == "(1, 2, 3)"
