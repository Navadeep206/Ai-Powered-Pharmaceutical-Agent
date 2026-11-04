"""Application Configuration Module using Pydantic Settings.

Provides centralized, type-safe settings loaded from environment variables
or .env files with safe non-secret defaults.
"""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for backend where .env is stored
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Central configuration for the RootIQ Backend Service."""

    model_config = SettingsConfigDict(
        env_file=(str(ENV_PATH), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "RootIQ API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database Configuration (Placeholder safe default)
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres_password@localhost:5432/rootiq_db"

    # AI / LLM Configuration (Placeholder safe default)
    GROQ_API_KEY: str = "gsk_placeholder_replace_with_actual_key"

    # Frontend Integration
    FRONTEND_URL: str = "http://localhost:5173"

    # Default allowed origins for CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


settings = Settings()
