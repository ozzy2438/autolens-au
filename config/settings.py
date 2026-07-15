"""AutoLens AU configuration settings."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "models" / "artifacts"


def _project_path_from_env(name: str, default: Path) -> Path:
    configured = Path(os.getenv(name, str(default)))
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


@dataclass
class DatabaseConfig:
    """Runtime database configuration with Snowflake production support."""

    backend: str = field(default_factory=lambda: os.getenv("DATABASE_BACKEND", "").lower())
    host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    name: str = field(default_factory=lambda: os.getenv("DB_NAME", "autolens_au"))
    user: str = field(default_factory=lambda: os.getenv("DB_USER", "autolens"))
    password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))
    snowflake_account: str = field(default_factory=lambda: os.getenv("SNOWFLAKE_ACCOUNT", ""))
    snowflake_user: str = field(default_factory=lambda: os.getenv("SNOWFLAKE_USER", ""))
    snowflake_password: str = field(default_factory=lambda: os.getenv("SNOWFLAKE_PASSWORD", ""))
    snowflake_private_key: str = field(
        default_factory=lambda: os.getenv("SNOWFLAKE_PRIVATE_KEY", "")
    )
    snowflake_private_key_path: str = field(
        default_factory=lambda: os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", "")
    )
    snowflake_private_key_passphrase: str = field(
        default_factory=lambda: os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "")
    )
    snowflake_database: str = field(
        default_factory=lambda: os.getenv("SNOWFLAKE_DATABASE", "AUTOLENS_AU")
    )
    snowflake_schema: str = field(default_factory=lambda: os.getenv("SNOWFLAKE_SCHEMA", "RAW"))
    snowflake_warehouse: str = field(
        default_factory=lambda: os.getenv("SNOWFLAKE_WAREHOUSE", "AUTOLENS_WH")
    )
    snowflake_role: str = field(default_factory=lambda: os.getenv("SNOWFLAKE_ROLE", "AUTOLENS_APP"))
    snowflake_query_tag: str = field(
        default_factory=lambda: os.getenv("SNOWFLAKE_QUERY_TAG", "autolens_runtime")
    )

    @property
    def resolved_backend(self) -> str:
        """Select an explicit backend, otherwise infer Snowflake from its account setting."""
        backend = self.backend or ("snowflake" if self.snowflake_account else "postgresql")
        if backend in {"postgres", "postgresql"}:
            return "postgresql"
        if backend == "snowflake":
            return backend
        raise ValueError("DATABASE_BACKEND must be 'postgresql' or 'snowflake'")

    @property
    def url(self) -> str:
        """PostgreSQL SQLAlchemy URL used for local development and secretless CI."""
        return os.getenv(
            "DATABASE_URL",
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}",
        )


@dataclass
class NSWFuelConfig:
    """NSW Fuel API configuration."""

    api_key: str = field(default_factory=lambda: os.getenv("NSW_FUEL_API_KEY", ""))
    api_secret: str = field(default_factory=lambda: os.getenv("NSW_FUEL_API_SECRET", ""))
    base_url: str = "https://api.onegov.nsw.gov.au"
    token_url: str = "https://api.onegov.nsw.gov.au/oauth/client_credential/accesstoken"
    prices_url: str = "https://api.onegov.nsw.gov.au/FuelPriceCheck/v2/fuel/prices"
    ref_data_url: str = "https://api.onegov.nsw.gov.au/FuelCheckRefData/v2/fuel/lovs"


@dataclass
class ModelConfig:
    """ML model configuration."""

    model_path: Path = field(
        default_factory=lambda: _project_path_from_env(
            "MODEL_PATH", MODEL_DIR / "hedonic_model_latest.joblib"
        )
    )
    version: str = field(default_factory=lambda: os.getenv("MODEL_VERSION", "1.0.0"))
    drift_threshold: float = 0.05  # 5% MAE degradation triggers retrain
    prediction_interval: float = 0.80  # 80% prediction interval
    random_state: int = 42
    test_size: float = 0.2
    # LightGBM hyperparameters
    lgbm_params: dict = field(
        default_factory=lambda: {
            "n_estimators": 500,
            "learning_rate": 0.05,
            "max_depth": 8,
            "num_leaves": 63,
            "min_child_samples": 20,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 0.1,
            "random_state": 42,
            "verbose": -1,
        }
    )


@dataclass
class AppConfig:
    """Application-level configuration."""

    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    api_host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    api_port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))


# Singleton instances
db_config = DatabaseConfig()
nsw_fuel_config = NSWFuelConfig()
model_config = ModelConfig()
app_config = AppConfig()
