"""Unit tests for depreciation curve analysis."""

import pytest
import numpy as np
import pandas as pd


class TestExponentialDecay:
    """Test exponential depreciation model."""
    
    def test_initial_value_at_age_zero(self):
        """At age 0, vehicle should retain full value."""
        from src.models.depreciation import exponential_decay
        
        result = exponential_decay(np.array([0.0]), 50000.0, 0.15)
        assert abs(result[0] - 50000.0) < 0.01
    
    def test_value_decreases_with_age(self):
        """Value should decrease monotonically with age."""
        from src.models.depreciation import exponential_decay
        
        ages = np.array([0, 1, 2, 3, 5, 10])
        values = exponential_decay(ages, 50000.0, 0.15)
        
        for i in range(1, len(values)):
            assert values[i] < values[i-1]
    
    def test_decay_rate_affects_speed(self):
        """Higher decay rate should mean faster depreciation."""
        from src.models.depreciation import exponential_decay
        
        age = np.array([5.0])
        slow = exponential_decay(age, 50000.0, 0.10)[0]
        fast = exponential_decay(age, 50000.0, 0.20)[0]
        
        assert slow > fast  # Slower decay retains more value


class TestRetentionCurve:
    """Test retention curve computation."""
    
    def test_empty_dataframe_returns_empty(self):
        """Empty input should return empty output."""
        from src.models.depreciation import compute_retention_curve
        
        df = pd.DataFrame(columns=["age", "price", "brand"])
        result = compute_retention_curve(df, "brand", "Toyota")
        assert result.empty
    
    def test_retention_starts_near_100(self):
        """New vehicles should have ~100% retention."""
        from src.models.depreciation import compute_retention_curve
        
        # Create sample data with clear age-price relationship
        df = pd.DataFrame({
            "age": [0, 0, 1, 1, 2, 2, 3, 3, 5, 5, 10, 10],
            "price": [50000, 48000, 44000, 42000, 38000, 36000,
                     33000, 31000, 25000, 23000, 15000, 13000],
            "brand": ["Toyota"] * 12,
        })
        
        result = compute_retention_curve(df, "brand", "Toyota")
        assert not result.empty
        # First retention value should be 100%
        assert result.iloc[0]["retention_pct"] == 100.0


class TestSegmentComparison:
    """Test segment comparison functionality."""
    
    def test_compare_segments_output_format(self):
        """Comparison should have expected columns."""
        from src.models.depreciation import compare_segments
        
        # Mock curves
        curves = {
            "Toyota": pd.DataFrame({
                "age": [1, 3, 5, 7, 10],
                "retention_pct": [88, 70, 55, 44, 30],
            }),
            "BMW": pd.DataFrame({
                "age": [1, 3, 5, 7, 10],
                "retention_pct": [82, 60, 45, 35, 22],
            }),
        }
        
        result = compare_segments(curves)
        assert "segment" in result.columns
        assert "retention_3yr" in result.columns
        assert len(result) == 2
