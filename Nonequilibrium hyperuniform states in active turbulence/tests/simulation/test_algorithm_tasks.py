"""
Tests for simulation/algorithm_tasks.py

Tests cover grid discretization, dealiasing, initial conditions, 
the PVC model, and time stepping scheme setup.
"""

import pytest
import numpy as np

import simulation.algorithm_tasks as tasks


class TestDiscretize:
    """Tests for the discretize function."""
    
    def test_grid_dimensions(self, small_grid):
        """Spatial and frequency grids should have correct shape."""
        L, N = small_grid['L'], small_grid['N']
        x_vectors, dx, k_vectors, dk = tasks.discretize(L=L, N=N)
        
        assert x_vectors.shape == (N, N, 2)
        assert k_vectors.shape == (N, N, 2)
    
    def test_discretization_factors(self, small_grid):
        """dx and dk should be computed correctly."""
        L, N = small_grid['L'], small_grid['N']
        x_vectors, dx, k_vectors, dk = tasks.discretize(L=L, N=N)
        
        assert dx == pytest.approx(L / N)
        assert dk == pytest.approx(2 * np.pi / L)
    
    def test_spatial_domain_bounds(self, small_grid):
        """Spatial domain should span [0, L)."""
        L, N = small_grid['L'], small_grid['N']
        x_vectors, _, _, _ = tasks.discretize(L=L, N=N)
        
        assert np.min(x_vectors[:,:,0]) >= 0
        assert np.max(x_vectors[:,:,0]) < L
    
    def test_minimum_grid_size(self):
        """Should work with N=4 (small but valid grid)."""
        x_vectors, dx, k_vectors, dk = tasks.discretize(L=1.0, N=4)
        
        assert x_vectors.shape == (4, 4, 2)
        assert k_vectors.shape == (4, 4, 2)


class TestDeAliasingRule:
    """Tests for the deAliasing_rule function."""
    
    def test_mask_shape(self, small_grid):
        """Mask should have same shape as grid."""
        L, N = small_grid['L'], small_grid['N']
        _, _, k_vectors, dk = tasks.discretize(L=L, N=N)
        k_square = k_vectors[:,:,0]**2 + k_vectors[:,:,1]**2
        
        mask = tasks.deAliasing_rule(k_square, N, dk)
        
        assert mask.shape == (N, N)
    
    def test_mask_is_boolean(self, small_grid):
        """Mask should be boolean array."""
        L, N = small_grid['L'], small_grid['N']
        _, _, k_vectors, dk = tasks.discretize(L=L, N=N)
        k_square = k_vectors[:,:,0]**2 + k_vectors[:,:,1]**2
        
        mask = tasks.deAliasing_rule(k_square, N, dk)
        
        assert mask.dtype == np.bool_
    
    def test_low_k_included(self, small_grid):
        """Low wavenumbers should be included (True)."""
        L, N = small_grid['L'], small_grid['N']
        _, _, k_vectors, dk = tasks.discretize(L=L, N=N)
        k_square = k_vectors[:,:,0]**2 + k_vectors[:,:,1]**2
        
        mask = tasks.deAliasing_rule(k_square, N, dk)
        
        # Origin should always be included
        assert mask[0, 0] == True


class TestSetInitialConditions:
    """Tests for the set_initial_conditions function."""
    
    def test_shape(self, small_grid):
        """Initial condition should have correct shape."""
        N = small_grid['N']
        w_k = tasks.set_initial_conditions(N)
        
        assert w_k.shape == (N, N)
    
    def test_dtype_complex(self, small_grid):
        """Fourier coefficients should be complex."""
        N = small_grid['N']
        w_k = tasks.set_initial_conditions(N)
        
        assert np.iscomplexobj(w_k)
    
    def test_nonzero(self, small_grid):
        """Should contain non-zero values."""
        N = small_grid['N']
        w_k = tasks.set_initial_conditions(N)
        
        assert np.any(w_k != 0)


class TestModelProblem:
    """Tests for the model_problem function (PVC viscosity)."""
    
    def test_output_shape(self, small_grid):
        """Viscosity should have same shape as k_norm."""
        N = small_grid['N']
        k_norm = np.random.rand(N, N) * 20
        
        v_eff = tasks.model_problem(k_norm, K_MIN=5, K_MAX=10, V_0=1.0, V_RATIO=2.0)
        
        assert v_eff.shape == (N, N)
    
    def test_low_k_positive_viscosity(self):
        """k < k_min should have positive viscosity V_0."""
        k_norm = np.array([[1, 2], [3, 4]])
        
        v_eff = tasks.model_problem(k_norm, K_MIN=5, K_MAX=10, V_0=1.0, V_RATIO=2.0)
        
        assert np.all(v_eff == 1.0)
    
    def test_active_range_negative_viscosity(self):
        """k_min <= k <= k_max should have negative viscosity."""
        k_norm = np.array([[6, 7], [8, 9]])
        
        v_eff = tasks.model_problem(k_norm, K_MIN=5, K_MAX=10, V_0=1.0, V_RATIO=2.0)
        
        assert np.all(v_eff == -2.0)  # -V_RATIO * V_0
    
    def test_high_k_strong_viscosity(self):
        """k > k_max should have strong positive viscosity 10*V_0."""
        k_norm = np.array([[15, 20], [25, 30]])
        
        v_eff = tasks.model_problem(k_norm, K_MIN=5, K_MAX=10, V_0=1.0, V_RATIO=2.0)
        
        assert np.all(v_eff == 10.0)


class TestPrepareSteppingScheme:
    """Tests for the prepare_stepping_scheme function."""
    
    def test_returns_callables(self, small_grid):
        """Should return 4 callable functions."""
        L, N = small_grid['L'], small_grid['N']
        x_vectors, dx, k_vectors, dk = tasks.discretize(L=L, N=N)
        k_square = k_vectors[:,:,0]**2 + k_vectors[:,:,1]**2
        k_norm = np.sqrt(k_square)
        deAlias = tasks.deAliasing_rule(k_square, N, dk)
        v_eff = tasks.model_problem(k_norm, K_MIN=5, K_MAX=10, V_0=1.0, V_RATIO=2.0)
        
        time_step, velocity, cfl_controller, energy = tasks.prepare_stepping_scheme(
            STEPPING_SCHEME="RK3",
            v_eff=v_eff,
            k_vectors=k_vectors,
            k_square=k_square,
            deAlias=deAlias,
            COURANT=0.5,
            dx=dx,
            dk=dk,
            N=N
        )
        
        assert callable(time_step)
        assert callable(velocity)
        assert callable(cfl_controller)
        assert callable(energy)