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

if __name__ == "__main__":
    unittest.main()