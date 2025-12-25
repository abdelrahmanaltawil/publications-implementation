"""
Shared pytest fixtures and path configuration for the active_flow test suite.
"""

import sys
import pathlib

import pytest
import numpy as np
import scipy.fftpack as scipy

# Add src directory to Python path so imports work
src_path = pathlib.Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def small_grid():
    """Small 8x8 grid for quick tests."""
    return {
        'L': np.pi,
        'N': 8
    }


@pytest.fixture
def medium_grid():
    """Medium 32x32 grid for more thorough tests."""
    return {
        'L': np.pi,
        'N': 32
    }


@pytest.fixture
def sample_k_vectors(small_grid):
    """Generate sample wavenumber vectors."""
    L, N = small_grid['L'], small_grid['N']
    k_axis = 2 * np.pi * scipy.fftfreq(N, L/N)
    k_x, k_y = np.meshgrid(k_axis, k_axis)
    return np.stack((k_x, k_y), axis=2)


@pytest.fixture
def sample_x_vectors(small_grid):
    """Generate sample spatial vectors."""
    L, N = small_grid['L'], small_grid['N']
    axis = np.linspace(0, L, num=N, endpoint=False)
    x, y = np.meshgrid(axis, axis)
    return np.stack((x, y), axis=2)


@pytest.fixture
def sample_vorticity_fourier(small_grid):
    """Generate sample vorticity field in Fourier space."""
    N = small_grid['N']
    w = np.random.normal(0, 1, size=(N, N))
    return scipy.fft2(w)


@pytest.fixture
def sample_extrema():
    """Sample extrema positions for testing."""
    return np.array([
        [1.0, 1.0, 5.0],
        [2.0, 2.0, -3.0],
        [3.0, 1.5, 4.0],
        [1.5, 3.0, -2.0],
    ])


@pytest.fixture
def empty_extrema():
    """Empty extrema array for edge case testing."""
    return np.array([]).reshape(0, 3)
