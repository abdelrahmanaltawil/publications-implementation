import unittest
import numpy as np
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/helpers')))

from utils import get_runoff_integration_bounds


class TestGetRunoffIntegrationBounds(unittest.TestCase):
    """Unit tests for get_runoff_integration_bounds function in utils.py"""

    def setUp(self):
        """Set up test parameters matching the paper's example values."""
        self.params = {
            "h": 0.447,       # Imperviousness fraction
            "Sdi": 0.049,     # Impervious depression storage (mm)
            "Sil": 5.20,      # Pervious initial loss (mm)
            "fc": 0.36,       # Ultimate infiltration rate (mm/hr)
            "Sm": 4.90,       # Maximum infiltration storage (mm)
            "ts": 13.6        # Time to saturation (hrs)
        }
        
        # Pre-calculate thresholds for clarity
        # Sdd = Sil - Sdi
        self.Sdd = self.params["Sil"] - self.params["Sdi"]  # ~5.15
        # threshold1 = h * Sdd
        self.threshold1 = self.params["h"] * self.Sdd  # ~2.30
        # threshold2 = h * (Sdd + Sm)
        self.threshold2 = self.params["h"] * (self.Sdd + self.params["Sm"])  # ~4.49

    def test_condition_1_small_v0(self):
        """Test Case 1: 0 <= v0 <= threshold1 (small runoff volumes)"""
        v0 = 1.0  # Well below threshold1 (~2.30)
        
        bounds = get_runoff_integration_bounds(v0, self.params)
        
        # Should return exactly 1 integration region
        self.assertEqual(len(bounds), 1, "Expected 1 integration region for small v0")
        
        # Verify bounds structure has required keys
        required_keys = ['a', 'b', 'c', 'd']
        for key in required_keys:
            self.assertIn(key, bounds[0], f"Missing key '{key}' in bounds")
        
        # Test that bounds return callable functions with correct values
        t_test = np.array([1.0, 2.0, 3.0])
        
        # a(t) should return zeros
        a_vals = bounds[0]['a'](t_test)
        np.testing.assert_array_equal(a_vals, np.zeros(3), "a(t) should return zeros")
        
        # c(t) should return zeros (lower bound of v)
        c_vals = bounds[0]['c'](t_test)
        np.testing.assert_array_equal(c_vals, np.zeros(3), "c(t) should return zeros")

    def test_condition_2_medium_v0(self):
        """Test Case 2: threshold1 < v0 <= threshold2 (medium runoff volumes)"""
        v0 = 3.0  # Between threshold1 (~2.30) and threshold2 (~4.49)
        
        bounds = get_runoff_integration_bounds(v0, self.params)
        
        # Should return exactly 2 integration regions
        self.assertEqual(len(bounds), 2, "Expected 2 integration regions for medium v0")
        
        # Both regions should have required keys
        for i, region in enumerate(bounds):
            required_keys = ['a', 'b', 'c', 'd']
            for key in required_keys:
                self.assertIn(key, region, f"Missing key '{key}' in region {i}")

    def test_condition_3_large_v0(self):
        """Test Case 3: v0 > threshold2 (large runoff volumes)"""
        v0 = 10.0  # Well above threshold2 (~4.49)
        
        bounds = get_runoff_integration_bounds(v0, self.params)
        
        # Should return exactly 2 integration regions
        self.assertEqual(len(bounds), 2, "Expected 2 integration regions for large v0")
        
        # First region: a=0 to b=ts
        t_test = np.array([1.0])
        a_val = bounds[0]['a'](t_test)
        b_val = bounds[0]['b'](t_test)
        
        self.assertEqual(float(a_val[0]), 0.0, "First region should start at t=0")
        self.assertAlmostEqual(float(b_val[0]), self.params['ts'], places=2, 
                               msg="First region should end at t=ts")

    def test_edge_case_v0_at_threshold1(self):
        """Test edge case: v0 exactly at threshold1"""
        v0 = self.threshold1  # Exactly at threshold1
        
        bounds = get_runoff_integration_bounds(v0, self.params)
        
        # Should fall into condition 1 (0 <= v0 <= threshold1)
        self.assertEqual(len(bounds), 1, "v0 at threshold1 should give 1 region")

    def test_edge_case_v0_at_threshold2(self):
        """Test edge case: v0 exactly at threshold2"""
        v0 = self.threshold2  # Exactly at threshold2
        
        bounds = get_runoff_integration_bounds(v0, self.params)
        
        # Should fall into condition 2 (threshold1 < v0 <= threshold2)
        self.assertEqual(len(bounds), 2, "v0 at threshold2 should give 2 regions")

    def test_v0_zero(self):
        """Test v0 = 0 (no runoff)"""
        v0 = 0.0
        
        bounds = get_runoff_integration_bounds(v0, self.params)
        
        # Should return 1 region for v0 = 0
        self.assertEqual(len(bounds), 1, "v0=0 should give 1 region")

    def test_bounds_are_vectorized(self):
        """Test that bound functions handle numpy arrays properly"""
        v0 = 1.0
        bounds = get_runoff_integration_bounds(v0, self.params)
        
        # Test with array input
        t_array = np.linspace(0, 10, 100)
        
        # All bound functions should return arrays of same shape
        for bound in bounds:
            for key in ['a', 'b', 'c', 'd']:
                result = bound[key](t_array)
                self.assertEqual(result.shape, t_array.shape, 
                               f"{key}(t) should maintain array shape")


if __name__ == '__main__':
    unittest.main()
