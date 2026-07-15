"""Pydantic schemas for the AutoLens AU API.

Defines request and response models with validation.
Mirrors the structure of commercial valuation APIs.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# --- Request Models ---

class ValuationRequest(BaseModel):
    """Vehicle valuation request parameters."""
    
    brand: str = Field(..., description="Vehicle manufacturer (e.g., 'Toyota', 'BMW')")
    model: str = Field(..., description="Vehicle model (e.g., 'Camry', '3 Series')")
    year: int = Field(..., ge=1980, le=2027, description="Year of manufacture")
    kilometres: int = Field(..., ge=0, le=1000000, description="Odometer reading in km")
    body_type: Optional[str] = Field(None, description="Body type (Sedan, SUV, Hatchback, etc.)")
    fuel_type: Optional[str] = Field(None, description="Fuel type (Petrol, Diesel, Hybrid, Electric)")
    transmission: Optional[str] = Field(None, description="Transmission (Automatic, Manual)")
    drive_type: Optional[str] = Field(None, description="Drive type (FWD, RWD, AWD, 4WD)")
    condition: Optional[str] = Field("Used", description="Condition (New, Used, Demo)")
    location: Optional[str] = Field(None, description="Location (state or city, e.g., 'NSW', 'Melbourne VIC')")
    doors: Optional[int] = Field(None, ge=2, le=5, description="Number of doors")
    seats: Optional[int] = Field(None, ge=2, le=9, description="Number of seats")
    cylinders: Optional[int] = Field(None, ge=0, le=16, description="Number of engine cylinders (0 for EV)")
    
    @field_validator("brand", "model")
    @classmethod
    def strip_and_title(cls, v: str) -> str:
        return v.strip().title()
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "brand": "Toyota",
                    "model": "Camry",
                    "year": 2020,
                    "kilometres": 45000,
                    "body_type": "Sedan",
                    "fuel_type": "Petrol",
                    "transmission": "Automatic",
                    "drive_type": "FWD",
                    "condition": "Used",
                    "location": "Sydney NSW",
                }
            ]
        }
    }


# --- Response Models ---

class PriceDriver(BaseModel):
    """A factor influencing the valuation."""
    feature: str = Field(..., description="Feature name")
    impact_aud: float = Field(..., description="Impact on price in AUD (positive = increases value)")
    direction: str = Field(..., description="'positive' or 'negative'")
    description: str = Field(..., description="Human-readable explanation")


class ValuationResponse(BaseModel):
    """Vehicle valuation response."""
    
    # Core valuation
    point_estimate_aud: float = Field(..., description="Predicted market price (AUD)")
    lower_bound_aud: float = Field(..., description="Lower bound of confidence interval (AUD)")
    upper_bound_aud: float = Field(..., description="Upper bound of confidence interval (AUD)")
    confidence_level: float = Field(0.80, description="Confidence level (e.g., 0.80 = 80%)")
    
    # Context
    price_drivers: List[PriceDriver] = Field(
        default_factory=list,
        description="Top factors influencing this valuation (SHAP-based)"
    )
    segment_median_aud: Optional[float] = Field(
        None, description="Median price for this brand/model segment"
    )
    
    # Metadata
    model_version: str = Field(..., description="Model version used for this valuation")
    generated_at: datetime = Field(default_factory=datetime.now)
    disclaimer: str = Field(
        default=(
            "This is an estimated market value based on publicly available data. "
            "Actual transaction prices may vary based on condition, options, and market conditions."
        )
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool
    timestamp: datetime
    version: str


class ModelInfoResponse(BaseModel):
    """Model information response."""
    model_version: str
    trained_at: Optional[datetime] = None
    training_samples: Optional[int] = None
    overall_mae: Optional[float] = None
    overall_mdape: Optional[float] = None
    features_used: List[str] = Field(default_factory=list)
    last_refresh: Optional[datetime] = None


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
    status_code: int = 500
    timestamp: datetime = Field(default_factory=datetime.now)
