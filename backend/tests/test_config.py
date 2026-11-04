"""Tests for centralized application configuration."""

from app.core.config import Settings, settings


def test_settings_properties():
    """Verify that settings instance contains all required configuration keys."""
    assert settings.APP_NAME == "RootIQ API"
    assert settings.APP_VERSION == "1.0.0"
    assert isinstance(settings.DEBUG, bool)
    assert hasattr(settings, "DATABASE_URL")
    assert hasattr(settings, "GROQ_API_KEY")
    assert hasattr(settings, "FRONTEND_URL")
    assert isinstance(settings.CORS_ORIGINS, list)


def test_safe_defaults():
    """Verify default values provide safe non-secret placeholders."""
    test_settings = Settings()
    assert test_settings.APP_NAME == "RootIQ API"
    assert "gsk_" in test_settings.GROQ_API_KEY
    assert "postgresql" in test_settings.DATABASE_URL
    assert test_settings.FRONTEND_URL.startswith("http")

