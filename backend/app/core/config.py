"""Application Configuration Module using Pydantic Settings.

Provides centralized, type-safe settings loaded from environment variables
or .env files with safe non-secret defaults.
"""

from pathlib import Path
from typing import List
from urllib.parse import urlparse
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

    # AI / LLM Configuration
    GROQ_API_KEY: str = "your_groq_api_key"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.0
    GROQ_MAX_TOKENS: int = 1024
    GROQ_TIMEOUT: float = 30.0

    @property
    def is_groq_configured(self) -> bool:
        """Verify whether a genuine, non-placeholder Groq API key is configured."""
        if not self.GROQ_API_KEY:
            return False
        cleaned = self.GROQ_API_KEY.strip()
        if not cleaned:
            return False
        # Filter known placeholder patterns
        if cleaned.startswith("gsk_placeholder") or cleaned in (
            "your_groq_api_key",
            "your_available_groq_model",
            "your_api_key",
            "gsk_placeholder_key",
            "gsk_placeholder_replace_with_actual_key",
        ):
            return False
        return True

    @property
    def safe_groq_api_key(self) -> str:
        """Return masked key for diagnostics without disclosing credentials."""
        if not self.is_groq_configured:
            return "not_configured"
        k = self.GROQ_API_KEY.strip()
        if len(k) <= 8:
            return "***"
        return f"{k[:4]}...{k[-4:]}"

    # Frontend Integration
    FRONTEND_URL: str = "http://localhost:5173"

    # Default allowed origins for CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    @property
    def safe_database_url(self) -> str:
        """Return masked database connection string without passwords for safe diagnostics."""
        try:
            parsed = urlparse(self.DATABASE_URL)
            if parsed.password:
                netloc = f"{parsed.username}:***@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                return parsed._replace(netloc=netloc).geturl()
            return self.DATABASE_URL
        except Exception:
            return "postgresql+psycopg://***"


settings = Settings()
