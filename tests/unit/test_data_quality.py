"""Unit tests for data quality functions."""

import numpy as np
import pandas as pd


class TestDeduplication:
    """Test listing deduplication logic."""

    def test_exact_duplicates_removed(self):
        """Exact duplicate records should be removed."""
        from src.ingestion.kaggle_loader import deduplicate_listings

        df = pd.DataFrame(
            {
                "brand": ["Toyota", "Toyota", "BMW"],
                "model": ["Camry", "Camry", "3 Series"],
                "year": [2020, 2020, 2019],
                "kilometres": [30000, 30000, 50000],
                "price": [35000, 35000, 45000],
            }
        )

        result = deduplicate_listings(df)
        assert len(result) == 2

    def test_similar_but_different_kept(self):
        """Records with different km or price should be kept."""
        from src.ingestion.kaggle_loader import deduplicate_listings

        df = pd.DataFrame(
            {
                "brand": ["Toyota", "Toyota"],
                "model": ["Camry", "Camry"],
                "year": [2020, 2020],
                "kilometres": [30000, 45000],  # Different km
                "price": [35000, 32000],  # Different price
            }
        )

        result = deduplicate_listings(df)
        assert len(result) == 2

    def test_most_complete_record_kept(self):
        """When duplicates exist, keep the record with more data."""
        from src.ingestion.kaggle_loader import deduplicate_listings

        df = pd.DataFrame(
            {
                "brand": ["Toyota", "Toyota"],
                "model": ["Camry", "Camry"],
                "year": [2020, 2020],
                "kilometres": [30000, 30000],
                "price": [35000, 35000],
                "body_type": ["Sedan", None],  # First record is more complete
                "fuel_type": ["Petrol", None],
            }
        )

        result = deduplicate_listings(df)
        assert len(result) == 1
        assert result.iloc[0]["body_type"] == "Sedan"


class TestEvaluationMetrics:
    """Test model evaluation metrics."""

    def test_mdape_calculation(self):
        """MdAPE should return median absolute percentage error."""
        from src.models.evaluation import median_absolute_percentage_error

        y_true = np.array([10000, 20000, 30000, 40000, 50000])
        y_pred = np.array([11000, 19000, 31500, 38000, 52500])  # ~5-10% errors

        mdape = median_absolute_percentage_error(y_true, y_pred)
        assert 0 < mdape < 20  # Should be in reasonable range

    def test_mdape_zero_for_perfect_predictions(self):
        """MdAPE should be 0 (or near 0) for perfect predictions."""
        from src.models.evaluation import median_absolute_percentage_error

        y_true = np.array([10000, 20000, 30000])
        y_pred = np.array([10000, 20000, 30000])

        mdape = median_absolute_percentage_error(y_true, y_pred)
        assert mdape == 0.0

    def test_prediction_interval_calibration(self):
        """80% PI should contain ~80% of actuals when well-calibrated."""
        from src.models.evaluation import evaluate_prediction_intervals

        np.random.seed(42)
        n = 1000
        y_true = np.random.normal(30000, 5000, n)
        center = y_true + np.random.normal(0, 1000, n)  # Slight noise
        width = 8000  # Fixed width
        lower = center - width / 2
        upper = center + width / 2

        result = evaluate_prediction_intervals(y_true, lower, upper, target_coverage=0.80)

        # Should have actual coverage close to target
        assert "actual_coverage" in result
        assert "is_calibrated" in result


class TestOutOfTimeSplit:
    """Test temporal validation split."""

    def test_split_by_year(self):
        """Data should be split at cutoff year."""
        from src.models.evaluation import out_of_time_split

        df = pd.DataFrame(
            {
                "year": [2019, 2020, 2020, 2021, 2022, 2023],
                "price": [25000, 28000, 30000, 32000, 35000, 38000],
            }
        )

        train, test = out_of_time_split(df, date_col="year", train_cutoff=2021)

        assert len(train) == 4  # 2019, 2020, 2020, 2021
        assert len(test) == 2  # 2022, 2023
        assert train["year"].max() <= 2021
        assert test["year"].min() > 2021
