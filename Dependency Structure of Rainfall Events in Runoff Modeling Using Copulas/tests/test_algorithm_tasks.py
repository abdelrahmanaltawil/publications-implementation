import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import os
import sys

# Add parent directory to path to allow importing algorithm_tasks
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import algorithm_tasks


class TestComputeCDF(unittest.TestCase):
    """Unit tests for compute_cdf function in algorithm_tasks.py"""

    def setUp(self):
        self.joint_densities = {
            "Gaussian": MagicMock(),
            "Clayton": MagicMock()
        }
        self.physical_params = {
            "h": 0.5, "Sdi": 0.1, "Sil": 0.2, "fc": 0.3, "Sm": 0.4, "ts": 10
        }
        self.analysis_params = {
            "v0_range_max": 5, # Creates 5 points
            "v0_limit": 100
        }
        self.integration_method = "ADAPTIVE_2D_QUADRATURE"
        self.kwargs = {"epsabs": 1e-5}

    @patch("algorithm_tasks.joblib.Parallel")
    @patch("algorithm_tasks.helpers.utils.get_integration_scheme")
    @patch("algorithm_tasks.helpers.utils.get_runoff_integration_bounds")
    def test_compute_cdf_basic(self, mock_get_bounds, mock_get_scheme, mock_parallel):
        """Test basic execution of compute_cdf with mocked dependencies."""
        
        # Mock Parallel to execute sequentially (return list of generator)
        def parallel_side_effect(n_jobs, verbose):
            def run(iterable):
                return [func(*args, **kwargs) for func, args, kwargs in iterable]
            return run
        mock_parallel.side_effect = parallel_side_effect

        # Mock integration scheme
        # The scheme function is called with (joint_density, a, b, c, d)
        mock_scheme_func = MagicMock(return_value=0.1)
        mock_get_scheme.return_value = mock_scheme_func

        # Mock bounds
        # Returns a list of dicts. Each dict has callables for a, b.
        mock_bounds = [
            {
                "a": MagicMock(return_value=0.0),
                "b": MagicMock(return_value=1.0),
                "c": MagicMock(),
                "d": MagicMock()
            }
        ]
        mock_get_bounds.return_value = mock_bounds

        # Execute function
        df = algorithm_tasks.compute_cdf(
            self.joint_densities,
            self.physical_params,
            self.analysis_params,
            self.integration_method,
            **self.kwargs
        )

        # Assertions
        self.assertIsInstance(df, pd.DataFrame)
        # v0_range_max is 5, so we expect 5 rows
        self.assertEqual(len(df), 5)
        self.assertListEqual(list(df.columns), ["v0", "Gaussian", "Clayton"])
        
        # Check values: 1 bound * 0.1 = 0.1
        expected_series = pd.Series([0.1] * 5, name="Gaussian")
        pd.testing.assert_series_equal(df["Gaussian"], expected_series, check_names=False)

        # Verify calls
        mock_get_scheme.assert_called_with(self.integration_method, **self.kwargs)
        # get_runoff_integration_bounds called for each point (5). It is pre-calculated once per v0, not per copula.
        self.assertEqual(mock_get_bounds.call_count, 5)

    @patch("algorithm_tasks.joblib.Parallel")
    @patch("algorithm_tasks.helpers.utils.get_integration_scheme")
    @patch("algorithm_tasks.helpers.utils.get_runoff_integration_bounds")
    def test_compute_cdf_multiple_bounds(self, mock_get_bounds, mock_get_scheme, mock_parallel):
        """Test compute_cdf when integration bounds return multiple segments."""
        
        mock_parallel.side_effect = lambda n_jobs, verbose: lambda iterable: [func(*args, **kwargs) for func, args, kwargs in iterable]
        
        # Scheme returns 0.2
        mock_get_scheme.return_value = MagicMock(return_value=0.2)

        # Bounds return 2 segments
        mock_bounds = [
            {"a": MagicMock(return_value=0), "b": MagicMock(return_value=1), "c": MagicMock(), "d": MagicMock()},
            {"a": MagicMock(return_value=2), "b": MagicMock(return_value=3), "c": MagicMock(), "d": MagicMock()}
        ]
        mock_get_bounds.return_value = mock_bounds

        df = algorithm_tasks.compute_cdf(
            {"TestCopula": MagicMock()},
            self.physical_params,
            self.analysis_params,
            self.integration_method
        )

        # 2 segments * 0.2 = 0.4
        self.assertTrue(np.allclose(df["TestCopula"], 0.4))

    def test_compute_cdf_empty_densities(self):
        """Test compute_cdf with empty joint_densities."""
        df = algorithm_tasks.compute_cdf(
            {},
            self.physical_params,
            self.analysis_params,
            self.integration_method
        )
        self.assertFalse(df.empty)
        self.assertListEqual(list(df.columns), ["v0"])

    @patch("algorithm_tasks.joblib.Parallel")
    @patch("algorithm_tasks.helpers.utils.get_integration_scheme")
    @patch("algorithm_tasks.helpers.utils.get_runoff_integration_bounds")
    def test_single_copula_family(self, mock_get_bounds, mock_get_scheme, mock_parallel):
        """Edge case: Single copula family."""
        mock_parallel.side_effect = lambda n_jobs, verbose: lambda iterable: [func(*args, **kwargs) for func, args, kwargs in iterable]
        mock_get_scheme.return_value = MagicMock(return_value=0.5)
        mock_get_bounds.return_value = [
            {"a": MagicMock(return_value=0), "b": MagicMock(return_value=1), "c": MagicMock(), "d": MagicMock()}
        ]

        df = algorithm_tasks.compute_cdf(
            {"SingleCopula": MagicMock()},
            self.physical_params,
            self.analysis_params,
            self.integration_method
        )
        
        self.assertEqual(len(df.columns), 2)  # v0 + SingleCopula
        self.assertIn("SingleCopula", df.columns)


class TestComputeReturnPeriod(unittest.TestCase):
    """Tests for compute_return_period function."""

    def test_basic_return_period_computation(self):
        """Test basic return period calculation."""
        # Create mock CDF results
        cdf_results = pd.DataFrame({
            "v0": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "Gaussian": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        })
        
        analysis_params = {
            "return_periods": [2, 5, 10],
            "events_per_year": 60
        }
        
        result = algorithm_tasks.compute_return_period(cdf_results, analysis_params)
        
        # Should have return period column and copula columns
        self.assertIn("ReturnPeriod", result.columns)
        self.assertIn("Gaussian", result.columns)
        self.assertEqual(len(result), 3)  # 3 return periods

    def test_multiple_copulas_return_period(self):
        """Test return period with multiple copulas."""
        cdf_results = pd.DataFrame({
            "v0": list(range(1, 21)),
            "Gaussian": np.linspace(0.05, 0.95, 20),
            "Clayton": np.linspace(0.1, 0.98, 20),
            "Gumbel": np.linspace(0.08, 0.92, 20)
        })
        
        analysis_params = {
            "return_periods": [2, 5, 10, 25, 50],
            "events_per_year": 60
        }
        
        result = algorithm_tasks.compute_return_period(cdf_results, analysis_params)
        
        self.assertIn("Gaussian", result.columns)
        self.assertIn("Clayton", result.columns)
        self.assertIn("Gumbel", result.columns)
        self.assertEqual(len(result), 5)

    def test_single_return_period(self):
        """Edge case: Single return period requested."""
        cdf_results = pd.DataFrame({
            "v0": list(range(1, 11)),
            "Gaussian": np.linspace(0.1, 0.9, 10)
        })
        
        analysis_params = {
            "return_periods": [100],
            "events_per_year": 60
        }
        
        result = algorithm_tasks.compute_return_period(cdf_results, analysis_params)
        
        self.assertEqual(len(result), 1)


class TestRunoffVolumeCDFClosedForm(unittest.TestCase):
    """Tests for runoff_volume_cdf_closed_form function."""

    def setUp(self):
        self.physical_params = {
            "h": 0.447,
            "Sdi": 0.049,
            "Sil": 5.20,
            "fc": 0.36,
            "Sm": 4.90,
            "ts": 13.6,
            "lambda_v": 0.1,  # 1/mean_volume
            "lambda_t": 0.2   # 1/mean_duration
        }
        self.analysis_params = {
            "v0_range_max": 10,
            "v0_limit": 100
        }

    def test_returns_array(self):
        """Verify function returns a numpy array."""
        result = algorithm_tasks.runoff_volume_cdf_closed_form(
            self.physical_params,
            self.analysis_params
        )
        
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), 10)

    def test_cdf_is_monotonic(self):
        """CDF should be monotonically increasing."""
        result = algorithm_tasks.runoff_volume_cdf_closed_form(
            self.physical_params,
            self.analysis_params
        )
        
        # CDF values should be non-decreasing (result is numpy array)
        diffs = np.diff(result)
        self.assertTrue(np.all(diffs >= 0), "CDF should be monotonically increasing")

    def test_cdf_bounded_0_1(self):
        """CDF values should be between 0 and 1."""
        result = algorithm_tasks.runoff_volume_cdf_closed_form(
            self.physical_params,
            self.analysis_params
        )
        
        self.assertTrue(np.all(result >= 0), "CDF values should be >= 0")
        self.assertTrue(np.all(result <= 1), "CDF values should be <= 1")

    def test_different_lambda_values(self):
        """Test with different exponential rate parameters."""
        # Higher lambda (smaller mean) should give faster CDF growth
        params_high_lambda = self.physical_params.copy()
        params_high_lambda["lambda_v"] = 0.5
        
        params_low_lambda = self.physical_params.copy()
        params_low_lambda["lambda_v"] = 0.05
        
        result_high = algorithm_tasks.runoff_volume_cdf_closed_form(
            params_high_lambda, self.analysis_params
        )
        result_low = algorithm_tasks.runoff_volume_cdf_closed_form(
            params_low_lambda, self.analysis_params
        )
        
        # Higher lambda should have higher CDF values (faster accumulation)
        self.assertGreater(result_high.mean(), result_low.mean())


class TestTailDependence(unittest.TestCase):
    """Tests for _compute_tail_dependence function."""

    def test_gumbel_upper_tail_only(self):
        """Gumbel copula should have upper tail dependence only."""
        # theta > 1 for Gumbel
        result = algorithm_tasks._compute_tail_dependence("Gumbel", 2.0)
        
        # Returns tuple (lower, upper)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        lower, upper = result
        self.assertEqual(lower, 0.0)
        self.assertGreater(upper, 0.0)

    def test_clayton_lower_tail_only(self):
        """Clayton copula should have lower tail dependence only."""
        result = algorithm_tasks._compute_tail_dependence("Clayton", 2.0)
        
        # Returns tuple (lower, upper)
        lower, upper = result
        self.assertEqual(upper, 0.0)
        self.assertGreater(lower, 0.0)

    def test_gaussian_no_tail_dependence(self):
        """Gaussian copula should have no tail dependence."""
        result = algorithm_tasks._compute_tail_dependence("Gaussian", 0.5)
        
        lower, upper = result
        self.assertEqual(upper, 0.0)
        self.assertEqual(lower, 0.0)

    def test_frank_no_tail_dependence(self):
        """Frank copula should have no tail dependence."""
        result = algorithm_tasks._compute_tail_dependence("Frank", 5.0)
        
        lower, upper = result
        self.assertEqual(upper, 0.0)
        self.assertEqual(lower, 0.0)


if __name__ == "__main__":
    unittest.main()