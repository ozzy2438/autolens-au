"""Valuation engine — business logic for the FastAPI endpoint.

Orchestrates:
- Model loading
- Feature preparation
- Prediction generation
- SHAP explanation
- Response formatting
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from config.settings import model_config, MODEL_DIR
from src.api.schemas import (
    ValuationRequest,
    ValuationResponse,
    PriceDriver,
    ModelInfoResponse,
)
from src.models.hedonic_model import (
    engineer_features,
    load_model,
    predict_price,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
)

logger = logging.getLogger(__name__)


class ValuationEngine:
    """Core valuation engine for the API."""
    
    def __init__(self):
        self.model = None
        self.model_version = model_config.version
        self.model_info: Dict = {}
    
    def load(self, model_path: Optional[Path] = None):
        """Load the trained model."""
        self.model = load_model(model_path)
        logger.info(f"Valuation engine loaded model v{self.model_version}")
    
    def valuate(self, request: ValuationRequest) -> ValuationResponse:
        """Generate valuation for a vehicle."""
        # Convert request to dict for model input
        vehicle_data = {
            "brand": request.brand,
            "model": request.model,
            "year": request.year,
            "kilometres": request.kilometres,
            "body_type": request.body_type or "Unknown",
            "fuel_type": request.fuel_type or "Unknown",
            "transmission": request.transmission or "Unknown",
            "drive_type": request.drive_type or "Unknown",
            "condition": request.condition or "Used",
            "location": request.location or "Unknown",
            "doors": request.doors or 4,
            "seats": request.seats or 5,
            "cylinders": request.cylinders or 4,
        }
        
        # Get prediction
        prediction = predict_price(self.model, vehicle_data, return_interval=True)
        
        # Generate price drivers (simplified SHAP-like explanations)
        drivers = self._compute_price_drivers(vehicle_data)
        
        return ValuationResponse(
            point_estimate_aud=prediction["point_estimate"],
            lower_bound_aud=prediction["lower_bound"],
            upper_bound_aud=prediction["upper_bound"],
            confidence_level=prediction["confidence_level"],
            price_drivers=drivers,
            segment_median_aud=None,  # TODO: compute from database
            model_version=self.model_version,
            generated_at=datetime.now(),
        )
    
    def _compute_price_drivers(self, vehicle_data: Dict) -> List[PriceDriver]:
        """Compute simplified price drivers.
        
        In production, this would use SHAP values from the model.
        This is a placeholder that provides directional explanations.
        """
        drivers = []
        current_year = datetime.now().year
        age = current_year - vehicle_data["year"]
        
        # Age impact
        if age <= 3:
            drivers.append(PriceDriver(
                feature="Vehicle Age",
                impact_aud=5000.0,
                direction="positive",
                description=f"Nearly new ({age} years old) — commands premium"
            ))
        elif age > 10:
            drivers.append(PriceDriver(
                feature="Vehicle Age",
                impact_aud=-8000.0,
                direction="negative",
                description=f"Older vehicle ({age} years) — significant depreciation"
            ))
        
        # Kilometres impact
        km = vehicle_data["kilometres"]
        avg_annual_km = 15000
        expected_km = age * avg_annual_km
        
        if km < expected_km * 0.7:
            drivers.append(PriceDriver(
                feature="Low Kilometres",
                impact_aud=3000.0,
                direction="positive",
                description=f"Below average km ({km:,} vs expected ~{expected_km:,})"
            ))
        elif km > expected_km * 1.5:
            drivers.append(PriceDriver(
                feature="High Kilometres",
                impact_aud=-4000.0,
                direction="negative",
                description=f"Above average km ({km:,} vs expected ~{expected_km:,})"
            ))
        
        # Brand impact (premium vs volume)
        premium_brands = ["BMW", "Mercedes-Benz", "Audi", "Lexus", "Porsche", "Land Rover"]
        if vehicle_data["brand"].title() in premium_brands:
            drivers.append(PriceDriver(
                feature="Premium Brand",
                impact_aud=8000.0,
                direction="positive",
                description=f"{vehicle_data['brand']} commands brand premium"
            ))
        
        return drivers[:5]  # Return top 5 drivers
    
    def get_model_info(self) -> ModelInfoResponse:
        """Return current model metadata."""
        return ModelInfoResponse(
            model_version=self.model_version,
            features_used=NUMERIC_FEATURES + CATEGORICAL_FEATURES,
        )
