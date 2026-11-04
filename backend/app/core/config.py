"""Application Configuration Module using Pydantic Settings."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the RootIQ Backend Service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "RootIQ API"
    APP_VERSION: str = "1.0.0"
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rootiq_db"
    GROQ_API_KEY: str = "gsk_placeholder"
    FRONTEND_URL: str = "http://localhost:5173"

    # Default allowed origins for CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


settings = Settings()
