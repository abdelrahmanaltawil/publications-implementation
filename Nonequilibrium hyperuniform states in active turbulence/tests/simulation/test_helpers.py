"""
Tests for simulation/helpers/time_stepping.py

Tests cover time integration schemes, CFL control, energy and velocity computations.
"""

import pytest
import numpy as np
import scipy.fftpack as scipy

import simulation.helpers.time_stepping as ts


class TestController:
    """Tests for the CFL controller function."""
    
    def test_basic_cfl(self):
        """tau = CFL * dx / max_u."""
        tau = ts.controller(courant=0.5, dx=0.1, max_u=1.0)
        
        assert tau == pytest.approx(0.05)
    
    def test_high_velocity_reduces_tau(self):
        """Higher velocity should give smaller time step."""
        tau_low = ts.controller(courant=0.5, dx=0.1, max_u=1.0)
        tau_high = ts.controller(courant=0.5, dx=0.1, max_u=10.0)
        
        assert tau_high < tau_low
    
    def test_zero_velocity_handling(self):
        """Should handle near-zero velocity (may give inf)."""
        tau = ts.controller(courant=0.5, dx=0.1, max_u=1e-10)
        
        # Should give very large tau
        assert tau > 1e6


class TestEnergyCalculation:
    """Tests for the energy_calculation function."""
    
    def test_positive_energy(self):
        """Energy should be non-negative."""
        N = 8
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        k_x, k_y = np.meshgrid(k_axis, k_axis)
        k_norm = np.sqrt(k_x**2 + k_y**2)
        dk = k_axis[1] - k_axis[0] if len(k_axis) > 1 else 1.0
        factor = dk
        U_k = np.abs(np.random.randn(N, N))**2
        
        E = ts.energy_calculation(k_norm, dk, N, factor, U_k)
        
        assert E >= 0
    
    def test_zero_velocity_zero_energy(self):
        """Zero velocity field should give zero energy."""
        N = 8
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        k_x, k_y = np.meshgrid(k_axis, k_axis)
        k_norm = np.sqrt(k_x**2 + k_y**2)
        dk = k_axis[1] - k_axis[0] if len(k_axis) > 1 else 1.0
        factor = dk
        U_k = np.zeros((N, N))
        
        E = ts.energy_calculation(k_norm, dk, N, factor, U_k)
        
        assert E == 0


class TestVelocityCalculation:
    """Tests for the velocity_calculation function."""
    
    def test_output_shapes(self):
        """Should return 4 arrays of correct shape."""
        N = 8
        w_k = np.random.randn(N, N) + 1j * np.random.randn(N, N)
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        k_x, k_y = np.meshgrid(k_axis, k_axis)
        k_square = k_x**2 + k_y**2
        k_inverse = np.zeros_like(k_square)
        k_inverse[k_square != 0] = 1 / k_square[k_square != 0]
        
        u, v, u_k, v_k = ts.velocity_calculation(w_k, k_x, k_y, k_inverse)
        
        assert u.shape == (N, N)
        assert v.shape == (N, N)
        assert u_k.shape == (N, N)
        assert v_k.shape == (N, N)
    
    def test_physical_velocity_is_real(self):
        """Physical space velocity should be real."""
        N = 8
        w_k = np.random.randn(N, N) + 1j * np.random.randn(N, N)
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        k_x, k_y = np.meshgrid(k_axis, k_axis)
        k_square = k_x**2 + k_y**2
        k_inverse = np.zeros_like(k_square)
        k_inverse[k_square != 0] = 1 / k_square[k_square != 0]
        
        u, v, u_k, v_k = ts.velocity_calculation(w_k, k_x, k_y, k_inverse)
        
        assert np.isrealobj(u)
        assert np.isrealobj(v)
    
    def test_zero_vorticity_zero_velocity(self):
        """Zero vorticity should give zero velocity."""
        N = 8
        w_k = np.zeros((N, N), dtype=complex)
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        k_x, k_y = np.meshgrid(k_axis, k_axis)
        k_square = k_x**2 + k_y**2
        k_inverse = np.zeros_like(k_square)
        k_inverse[k_square != 0] = 1 / k_square[k_square != 0]
        
        u, v, u_k, v_k = ts.velocity_calculation(w_k, k_x, k_y, k_inverse)
        
        assert np.allclose(u, 0)
        assert np.allclose(v, 0)


class TestSteppingScheme:
    """Tests for the stepping_scheme function."""
    
    def _setup_stepping_params(self, N=8):
        """Setup parameters for stepping scheme tests."""
        k_axis = np.fft.fftfreq(N, 1/N) * 2 * np.pi
        k_x, k_y = np.meshgrid(k_axis, k_axis)
        k_square = k_x**2 + k_y**2
        k_inverse = np.zeros_like(k_square)
        k_inverse[k_square != 0] = 1 / k_square[k_square != 0]
        deAlias = k_square < (2/3 * N/2 * 1.0)**2
        v_eff = np.ones_like(k_square) * 0.1
        
        return k_x, k_y, k_square, k_inverse, deAlias, v_eff
    
    def test_euler_scheme_output_shape(self):
        """Euler scheme should return same shape as input."""
        N = 8
        w_k = np.random.randn(N, N) + 1j * np.random.randn(N, N)
        k_x, k_y, k_square, k_inverse, deAlias, v_eff = self._setup_stepping_params(N)
        
        w_k_new = ts.stepping_scheme(
            w_k, tau=0.01, STEPPING_SCHEME="Euler Semi-Implicit",
            v_eff=v_eff, k_x=k_x, k_y=k_y, k_square=k_square,
            k_inverse=k_inverse, deAlias=deAlias
        )
        
        assert w_k_new.shape == w_k.shape
    
    def test_rk3_scheme_output_shape(self):
        """RK3 scheme should return same shape as input."""
        N = 8
        w_k = np.random.randn(N, N) + 1j * np.random.randn(N, N)
        k_x, k_y, k_square, k_inverse, deAlias, v_eff = self._setup_stepping_params(N)
        
        w_k_new = ts.stepping_scheme(
            w_k, tau=0.01, STEPPING_SCHEME="RK3",
            v_eff=v_eff, k_x=k_x, k_y=k_y, k_square=k_square,
            k_inverse=k_inverse, deAlias=deAlias
        )
        
        assert w_k_new.shape == w_k.shape
    
    def test_imex_scheme_output_shape(self):
        """IMEX scheme should return same shape as input."""
        N = 8
        w_k = np.random.randn(N, N) + 1j * np.random.randn(N, N)
        k_x, k_y, k_square, k_inverse, deAlias, v_eff = self._setup_stepping_params(N)
        
        w_k_new = ts.stepping_scheme(
            w_k, tau=0.01, STEPPING_SCHEME="IMEX Runge-Kutta",
            v_eff=v_eff, k_x=k_x, k_y=k_y, k_square=k_square,
            k_inverse=k_inverse, deAlias=deAlias
        )
        
        assert w_k_new.shape == w_k.shape
