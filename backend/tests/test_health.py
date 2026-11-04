"""Tests for the service health endpoint, API documentation, and CORS."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_app_startup():
    """Verify that FastAPI application initializes with correct metadata."""
    assert app.title == settings.APP_NAME
    assert app.version == settings.APP_VERSION


def test_health_endpoint():
    """Verify that GET /api/health returns 200 and expected payload."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "status": "healthy",
        "application": "RootIQ API",
        "version": "1.0.0",
    }
    assert "status" in data
    assert "application" in data
    assert "version" in data


def test_docs_endpoint():
    """Verify that Swagger documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_schema():
    """Verify that OpenAPI JSON schema matches title and version."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == settings.APP_NAME
    assert schema["info"]["version"] == settings.APP_VERSION


def test_cors_headers():
    """Verify that CORS response headers allow configured origins."""
    headers = {"Origin": settings.FRONTEND_URL}
    response = client.get("/api/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == settings.FRONTEND_URL
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_options():
    """Verify that CORS OPTIONS preflight request responds correctly."""
    headers = {
        "Origin": settings.FRONTEND_URL,
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == settings.FRONTEND_URL
