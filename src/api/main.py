"""FastAPI application for AutoLens AU Valuation API.

This API mirrors the shape of commercial valuation APIs (like RedBook's)
to demonstrate understanding of the product category.

Endpoints:
- POST /valuation: Get vehicle valuation with confidence interval
- GET /health: Service health check
- GET /model/info: Current model version and metrics

Auto-generated OpenAPI docs available at /docs (Swagger) and /redoc.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import (
    ValuationRequest,
    ValuationResponse,
    HealthResponse,
    ModelInfoResponse,
    ErrorResponse,
)
from src.api.valuation_engine import ValuationEngine

# Global valuation engine instance
engine: Optional[ValuationEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: load model on startup."""
    global engine
    try:
        engine = ValuationEngine()
        engine.load()
    except FileNotFoundError:
        # Model not yet trained — API will return 503 until model is available
        engine = None
    yield
    # Cleanup on shutdown
    engine = None


app = FastAPI(
    title="AutoLens AU Valuation API",
    description=(
        "Australian vehicle valuation API providing price estimates, "
        "depreciation data, and residual value projections. "
        "Independent public data product by Osman Orka."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Osman Orka",
        "url": "https://github.com/ozzy2438/autolens-au",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Service health check."""
    return HealthResponse(
        status="healthy" if engine is not None else "degraded",
        model_loaded=engine is not None,
        timestamp=datetime.now(),
        version="1.0.0",
    )


@app.get("/model/info", response_model=ModelInfoResponse, tags=["System"])
async def model_info():
    """Get current model version and performance metrics."""
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Please train the model first.",
        )
    
    return engine.get_model_info()


@app.post(
    "/valuation",
    response_model=ValuationResponse,
    responses={503: {"model": ErrorResponse}},
    tags=["Valuation"],
    summary="Get vehicle valuation",
    description=(
        "Submit vehicle parameters to receive a price estimate with "
        "confidence interval and SHAP-based explanation of key drivers."
    ),
)
async def get_valuation(request: ValuationRequest):
    """Generate vehicle valuation.
    
    Accepts vehicle characteristics and returns:
    - Point estimate (predicted market price in AUD)
    - Confidence interval (lower and upper bounds)
    - Key price drivers (SHAP-based explanations)
    - Comparable segment statistics
    """
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Valuation model not available. Service is starting up or model needs training.",
        )
    
    try:
        result = engine.valuate(request)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid vehicle parameters: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation failed: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
