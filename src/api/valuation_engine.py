"""Model-backed valuation business logic for the FastAPI endpoint."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config.settings import MODEL_DIR
from src.api.schemas import (
    ModelInfoResponse,
    PriceDriver,
    ValuationRequest,
    ValuationResponse,
)
from src.models.hedonic_model import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    ValuationModelBundle,
    explain_prediction,
    load_model,
    predict_price,
)

logger = logging.getLogger(__name__)


class ValuationEngine:
    """Load one calibrated artifact and expose consistent API responses."""

    def __init__(self) -> None:
        self.model: ValuationModelBundle | None = None
        self.model_info: dict[str, Any] = {}

    def load(self, model_path: Path | None = None) -> None:
        """Load the calibrated model and its measured metrics."""
        self.model = load_model(model_path)
        metrics_path = MODEL_DIR / "latest_metrics.json"
        if metrics_path.exists():
            self.model_info = json.loads(metrics_path.read_text(encoding="utf-8"))
        logger.info("Valuation engine loaded model v%s", self.model.version)

    def valuate(self, request: ValuationRequest) -> ValuationResponse:
        """Generate a calibrated valuation and actual local TreeSHAP drivers."""
        if self.model is None:
            raise RuntimeError("Valuation model is not loaded")
        vehicle_data: dict[str, Any] = {
            "brand": request.brand,
            "model": request.model,
            "variant": request.variant or "Unknown",
            "year": request.year,
            "kilometres": request.kilometres,
            "body_type": request.body_type or "Unknown",
            "fuel_type": request.fuel_type or "Unknown",
            "transmission": request.transmission or "Unknown",
            "drive_type": request.drive_type or "Unknown",
            "condition": request.condition or "Used",
            "location": request.location or "Unknown",
            "doors": request.doors if request.doors is not None else 4,
            "seats": request.seats if request.seats is not None else 5,
            "cylinders": request.cylinders if request.cylinders is not None else 4,
        }
        prediction = predict_price(self.model, vehicle_data, return_interval=True)
        drivers = [PriceDriver(**driver) for driver in explain_prediction(self.model, vehicle_data)]
        segment_key = f"{request.brand.strip().casefold()}|{request.model.strip().casefold()}"

        return ValuationResponse(
            point_estimate_aud=float(prediction["point_estimate"]),
            lower_bound_aud=float(prediction["lower_bound"]),
            upper_bound_aud=float(prediction["upper_bound"]),
            confidence_level=float(prediction["confidence_level"]),
            price_drivers=drivers,
            segment_median_aud=self.model.segment_medians_aud.get(segment_key),
            model_version=self.model.version,
            generated_at=datetime.now(UTC),
        )

    def get_model_info(self) -> ModelInfoResponse:
        """Return artifact metadata and only metrics that were actually measured."""
        if self.model is None:
            raise RuntimeError("Valuation model is not loaded")
        overall = self.model_info.get("lgbm_metrics", {}).get("overall", {})
        interval = self.model_info.get("prediction_interval_metrics", {})
        return ModelInfoResponse(
            model_version=self.model.version,
            trained_at=datetime.fromisoformat(self.model.trained_at),
            training_samples=self.model_info.get("fit_samples"),
            overall_mae=overall.get("mae"),
            overall_mdape=overall.get("mdape"),
            validation_strategy=self.model.validation_strategy,
            prediction_interval_coverage=interval.get("actual_coverage"),
            trained_through_snapshot=self.model.trained_through_snapshot,
            features_used=NUMERIC_FEATURES + CATEGORICAL_FEATURES,
            last_refresh=(
                datetime.fromisoformat(self.model.trained_at)
                if self.model.trained_through_snapshot
                else None
            ),
        )
