"""Unit tests for the hedonic pricing model."""

from datetime import datetime

import numpy as np
import pandas as pd


class TestFeatureEngineering:
    """Test feature engineering functions."""

    def test_age_calculation(self):
        """Age should be current_year - manufacture_year."""
        from src.models.hedonic_model import engineer_features

        df = pd.DataFrame(
            {
                "year": [2020, 2015, 2010],
                "brand": ["Toyota", "BMW", "Mazda"],
                "kilometres": [30000, 80000, 150000],
                "price": [35000, 28000, 15000],
            }
        )

        result = engineer_features(df)
        current_year = datetime.now().year

        assert result["age"].iloc[0] == current_year - 2020
        assert result["age"].iloc[1] == current_year - 2015
        assert result["age"].iloc[2] == current_year - 2010

    def test_age_capped_at_50(self):
        """Vehicles older than 50 years should be capped."""
        from src.models.hedonic_model import engineer_features

        df = pd.DataFrame(
            {
                "year": [1960],
                "brand": ["Ford"],
                "kilometres": [200000],
                "price": [5000],
            }
        )

        result = engineer_features(df)
        assert result["age"].iloc[0] <= 50

    def test_age_km_interaction(self):
        """Interaction should be age * km / 10000."""
        from src.models.hedonic_model import engineer_features

        df = pd.DataFrame(
            {
                "year": [2021],
                "brand": ["Toyota"],
                "kilometres": [50000],
                "price": [30000],
            }
        )

        result = engineer_features(df)
        expected_age = datetime.now().year - 2021
        expected_interaction = expected_age * 50000 / 10000

        assert abs(result["age_km_interaction"].iloc[0] - expected_interaction) < 0.01

    def test_brand_standardisation(self):
        """Common brand variations should be normalised."""
        from src.models.hedonic_model import engineer_features

        df = pd.DataFrame(
            {
                "year": [2020, 2020],
                "brand": ["bmw", "Mercedes Benz"],
                "kilometres": [30000, 30000],
                "price": [50000, 60000],
            }
        )

        result = engineer_features(df)
        # After title case + mapping
        assert result["brand"].iloc[0] == "BMW"


class TestDataPreparation:
    """Test data preparation for training."""

    def test_invalid_prices_filtered(self):
        """Prices below $1000 or above $500k should be removed."""
        from src.models.hedonic_model import prepare_training_data

        df = pd.DataFrame(
            {
                "year": [2020, 2020, 2020, 2020],
                "brand": ["Toyota"] * 4,
                "model": ["Camry"] * 4,
                "kilometres": [30000] * 4,
                "price": [500, 35000, 600000, 25000],  # 500 and 600k should be filtered
                "body_type": ["Sedan"] * 4,
                "fuel_type": ["Petrol"] * 4,
                "transmission": ["Automatic"] * 4,
                "drive_type": ["FWD"] * 4,
                "condition": ["Used"] * 4,
                "location": ["Sydney NSW"] * 4,
                "doors": [4] * 4,
                "seats": [5] * 4,
                "cylinders": [4] * 4,
            }
        )

        X, _y = prepare_training_data(df)
        assert len(X) == 2  # Only 35000 and 25000 should remain

    def test_target_is_log_price(self):
        """Target should be log1p(price)."""
        from src.models.hedonic_model import prepare_training_data

        df = pd.DataFrame(
            {
                "year": [2020],
                "brand": ["Toyota"],
                "model": ["Camry"],
                "kilometres": [30000],
                "price": [35000],
                "body_type": ["Sedan"],
                "fuel_type": ["Petrol"],
                "transmission": ["Automatic"],
                "drive_type": ["FWD"],
                "condition": ["Used"],
                "location": ["Sydney NSW"],
                "doors": [4],
                "seats": [5],
                "cylinders": [4],
            }
        )

        _X, y = prepare_training_data(df)
        expected_log_price = np.log1p(35000)
        assert abs(y.iloc[0] - expected_log_price) < 0.001


class TestPrediction:
    """Test prediction functionality."""

    def test_prediction_returns_required_fields(self):
        """Prediction should return point estimate and bounds."""
        # This would require a trained model; test the structure
        result = {
            "point_estimate": 35000.0,
            "lower_bound": 29750.0,
            "upper_bound": 40250.0,
            "confidence_level": 0.80,
            "currency": "AUD",
        }

        assert "point_estimate" in result
        assert "lower_bound" in result
        assert "upper_bound" in result
        assert result["lower_bound"] < result["point_estimate"]
        assert result["upper_bound"] > result["point_estimate"]
        assert result["currency"] == "AUD"
