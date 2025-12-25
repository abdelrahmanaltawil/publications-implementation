"""
Tests for hyperuniformity_analysis/algorithm_tasks.py

Tests cover structure factor computation, radial profiles, and curve fitting.
"""

import pytest
import numpy as np

import hyperuniformity_analysis.algorithm_tasks as tasks
import hyperuniformity_analysis.helpers.register as re


@pytest.fixture(autouse=True)
def init_register():
    """Initialize register before each test."""
    re.init_register()


class TestDensityFourier:
    """Tests for the _density_fourier function."""
    
    def test_output_shape(self, small_grid, sample_extrema):
        """Output should have shape (N, N)."""
        N = small_grid['N']
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        kx, ky = np.meshgrid(k_axis, k_axis)
        
        density, count = tasks._density_fourier(kx, ky, sample_extrema)
        
        assert density.shape == (N, N)
    
    def test_returns_particle_count(self, small_grid, sample_extrema):
        """Should return correct number of particles."""
        N = small_grid['N']
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        kx, ky = np.meshgrid(k_axis, k_axis)
        
        density, count = tasks._density_fourier(kx, ky, sample_extrema)
        
        assert count == len(sample_extrema)
    
    def test_zero_at_origin(self, small_grid, sample_extrema):
        """Density should be zero at k=0 (due to implementation)."""
        N = small_grid['N']
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        kx, ky = np.meshgrid(k_axis, k_axis)
        
        density, _ = tasks._density_fourier(kx, ky, sample_extrema)
        
        # Origin is at [0,0] for fftfreq ordering
        assert density[0, 0] == 0


class TestStructureFactor:
    """Tests for the _structure_factor function."""
    
    def test_output_shape(self, small_grid, sample_extrema):
        """S(k) should have shape (N, N)."""
        N = small_grid['N']
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        kx, ky = np.meshgrid(k_axis, k_axis)
        
        S_k = tasks._structure_factor(kx, ky, sample_extrema)
        
        assert S_k.shape == (N, N)
    
    def test_non_negative(self, small_grid, sample_extrema):
        """S(k) should be non-negative (it's |ñ|²/N)."""
        N = small_grid['N']
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        kx, ky = np.meshgrid(k_axis, k_axis)
        
        S_k = tasks._structure_factor(kx, ky, sample_extrema)
        
        assert np.all(S_k >= 0)
    
    def test_real_valued(self, small_grid, sample_extrema):
        """S(k) should be real valued."""
        N = small_grid['N']
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        kx, ky = np.meshgrid(k_axis, k_axis)
        
        S_k = tasks._structure_factor(kx, ky, sample_extrema)
        
        assert np.isrealobj(S_k)


class TestRadialProfile:
    """Tests for the radial_profile function."""
    
    def test_output_is_dict(self, small_grid, sample_extrema):
        """Should return dict of radial profiles."""
        N = small_grid['N']
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        kx, ky = np.meshgrid(k_axis, k_axis)
        
        # Create structure factor dict
        S_k = tasks._structure_factor(kx, ky, sample_extrema)
        structure_factor_snapshots = {"test": S_k}
        
        result = tasks.radial_profile(kx, ky, structure_factor_snapshots)
        
        assert isinstance(result, dict)
        assert "test" in result
    
    def test_output_is_1d(self, small_grid, sample_extrema):
        """Radial profile should be 1D array."""
        N = small_grid['N']
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        kx, ky = np.meshgrid(k_axis, k_axis)
        
        S_k = tasks._structure_factor(kx, ky, sample_extrema)
        structure_factor_snapshots = {"test": S_k}
        
        result = tasks.radial_profile(kx, ky, structure_factor_snapshots)
        
        assert result["test"].ndim == 1


class TestLinearCurveFitting:
    """Tests for the _linear_curve_fitting function."""
    
    def test_perfect_line(self):
        """Should fit perfect line exactly."""
        x = np.array([1, 2, 3, 4, 5])
        y = 2 * x + 3  # slope=2, intercept=3
        
        slope, intercept, r_squared = tasks._linear_curve_fitting(x, y)
        
        assert slope == pytest.approx(2.0)
        assert intercept == pytest.approx(3.0)
        assert r_squared == pytest.approx(1.0)
    
    def test_noisy_data(self):
        """Should still return reasonable fit for noisy data."""
        np.random.seed(42)
        x = np.linspace(0, 10, 50)
        y = 2 * x + 3 + np.random.randn(50) * 0.5
        
        slope, intercept, r_squared = tasks._linear_curve_fitting(x, y)
        
        assert 1.8 < slope < 2.2  # Close to 2
        assert 2.5 < intercept < 3.5  # Close to 3
        assert r_squared > 0.9  # Good fit
