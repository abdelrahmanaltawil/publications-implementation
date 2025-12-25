"""
Tests for extrema_search/algorithm_tasks.py

Tests cover vorticity computation, grid creation, extrema finding, and boundary detection.
"""

import pytest
import numpy as np
import scipy.fftpack as scipy

import extrema_search.algorithm_tasks as tasks
import extrema_search.helpers.register as re


@pytest.fixture(autouse=True)
def init_register():
    """Initialize register before each test."""
    re.init_register()


class TestComputeVorticity:
    """Tests for the compute_vorticity function."""
    
    def test_output_is_real(self, sample_vorticity_fourier):
        """Physical vorticity should be real."""
        snapshots = {"test": sample_vorticity_fourier}
        
        result = tasks.compute_vorticity(snapshots)
        
        assert np.isrealobj(result["test"])
    
    def test_shape_preserved(self, sample_vorticity_fourier):
        """Output shape should match input."""
        snapshots = {"test": sample_vorticity_fourier}
        
        result = tasks.compute_vorticity(snapshots)
        
        assert result["test"].shape == sample_vorticity_fourier.shape
    
    def test_multiple_snapshots(self, small_grid):
        """Should handle multiple snapshots."""
        N = small_grid['N']
        snapshots = {
            "snap1": np.random.randn(N, N) + 1j * np.random.randn(N, N),
            "snap2": np.random.randn(N, N) + 1j * np.random.randn(N, N),
        }
        
        result = tasks.compute_vorticity(snapshots)
        
        assert len(result) == 2
        assert "snap1" in result
        assert "snap2" in result


class TestAtBoundary:
    """Tests for the at_boundary function."""
    
    def test_corners_are_boundary(self):
        """All 4 corners should be boundary."""
        end = 10
        
        assert tasks.at_boundary(0, 0, end) == True
        assert tasks.at_boundary(0, end, end) == True
        assert tasks.at_boundary(end, 0, end) == True
        assert tasks.at_boundary(end, end, end) == True
    
    def test_edges_are_boundary(self):
        """All edge points should be boundary."""
        end = 10
        
        # Top edge
        assert tasks.at_boundary(0, 5, end) == True
        # Bottom edge  
        assert tasks.at_boundary(end, 5, end) == True
        # Left edge
        assert tasks.at_boundary(5, 0, end) == True
        # Right edge
        assert tasks.at_boundary(5, end, end) == True
    
    def test_interior_not_boundary(self):
        """Interior points should not be boundary."""
        end = 10
        
        assert tasks.at_boundary(5, 5, end) == False
        assert tasks.at_boundary(1, 1, end) == False
        assert tasks.at_boundary(9, 9, end) == False


class TestFindExtrema:
    """Tests for the find_extrema function."""
    
    def test_empty_result_structure(self):
        """Should return dict with correct structure."""
        # Create a minimal grid
        grids = {}
        
        result = tasks.find_extrema(grids, threshold=None)
        
        assert isinstance(result, dict)
    
    def test_threshold_filters_weak_extrema(self, small_grid):
        """High threshold should filter out weak extrema."""
        N = small_grid['N']
        L = small_grid['L']
        
        # Create simple test data
        axis = np.linspace(0, L, num=N, endpoint=False)
        x, y = np.meshgrid(axis, axis)
        
        # Create vorticity field with known extrema
        w = np.sin(2 * x) * np.sin(2 * y)
        w_k = {"test": scipy.fft2(w)}
        
        # Get vorticity in physical space
        w_physical = tasks.compute_vorticity(w_k)
        
        # Create grid
        grids = tasks._create_grid(x, y, w_physical["test"])
        
        # Find extrema with no threshold
        result_no_thresh = tasks.find_extrema({"test_grid": grids}, threshold=None)
        
        # Find extrema with high threshold
        result_high_thresh = tasks.find_extrema({"test_grid": grids}, threshold=1000)
        
        # High threshold should give fewer (or equal) extrema
        if len(result_no_thresh) > 0:
            for key in result_no_thresh:
                all_no_thresh = len(result_no_thresh[key]["All Extrema"])
                all_high_thresh = len(result_high_thresh[key]["All Extrema"])
                assert all_high_thresh <= all_no_thresh
