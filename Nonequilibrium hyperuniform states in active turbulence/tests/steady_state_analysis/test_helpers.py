"""
Tests for steady_state_analysis/helpers/check_snapshots.py

Tests cover snapshot location parsing including range expansion and validation.
"""

import pytest
import numpy as np

from steady_state_analysis.helpers.check_snapshots import parse_snapshots


class TestParseSnapshots:
    """Tests for the parse_snapshots function."""
    
    def test_single_value(self):
        """Single value should be parsed correctly."""
        result = parse_snapshots(["10000"])
        
        assert result == [10000]
    
    def test_multiple_values(self):
        """Multiple single values should all be included."""
        result = parse_snapshots(["10000", "20000", "30000"])
        
        assert result == [10000, 20000, 30000]
    
    def test_range_expansion(self):
        """Range should expand to all 1000-step values."""
        result = parse_snapshots(["10000:13000"])
        
        assert result == [10000, 11000, 12000, 13000]
    
    def test_mixed_values_and_ranges(self):
        """Should handle mix of single values and ranges."""
        result = parse_snapshots(["5000", "10000:12000", "20000"])
        
        assert 5000 in result
        assert 10000 in result
        assert 11000 in result
        assert 12000 in result
        assert 20000 in result
    
    def test_invalid_non_multiple_of_1000(self):
        """Should raise ValueError for non-1000 multiples."""
        with pytest.raises(ValueError) as excinfo:
            parse_snapshots(["10500"])
        
        assert "factor of 1000" in str(excinfo.value)
    
    def test_range_with_invalid_value(self):
        """Range that produces non-1000 multiples should fail."""
        with pytest.raises(ValueError):
            parse_snapshots(["10500:11500"])
    
    def test_empty_list(self):
        """Empty list should return empty list."""
        result = parse_snapshots([])
        
        assert result == []
    
    def test_large_range(self):
        """Should handle large ranges efficiently."""
        result = parse_snapshots(["100000:200000"])
        
        assert len(result) == 101  # 100 intervals + 1
        assert result[0] == 100000
        assert result[-1] == 200000
