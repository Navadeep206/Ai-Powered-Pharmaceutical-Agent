"""Tests for the service health endpoint and API documentation."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify that GET /api/health returns 200 and expected payload."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "application": "RootIQ API",
        "version": "1.0.0",
    }


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
    assert schema["info"]["title"] == "RootIQ API"
    assert schema["info"]["version"] == "1.0.0"

