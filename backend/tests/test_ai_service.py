"""Unit and integration tests for Groq AI LLM connection, configuration, and health probing."""

from unittest.mock import MagicMock, patch
import httpx
import pytest
import groq
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from app.core.config import Settings, settings
from app.core.exceptions import AIConfigurationError
from app.main import app
from app.services.ai_service import AIService, ai_service

client = TestClient(app)

DUMMY_VALID_KEY = "gsk_testvalidkey1234567890abcdefghijklmnopqrstuvwxyz"
DUMMY_HTTPX_REQ = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")


@pytest.fixture(autouse=True)
def reset_ai_service_client():
    """Ensure each test starts with a clean AI service client cache."""
    ai_service._client = None
    ai_service._cached_config_key = None
    yield
    ai_service._client = None
    ai_service._cached_config_key = None


# 1. Missing / Unconfigured API Key Tests
def test_missing_api_key_configuration():
    """Verify that empty or placeholder API key returns Not configured status and raises AIConfigurationError on client request."""
    with patch.object(settings, "GROQ_API_KEY", "your_groq_api_key"):
        assert settings.is_groq_configured is False
        assert settings.safe_groq_api_key == "not_configured"

        # Direct client instantiation raises configuration error
        with pytest.raises(AIConfigurationError) as exc_info:
            ai_service.get_client(force_refresh=True)
        assert "not configured" in str(exc_info.value.message).lower()

        # Connection test returns structured Not configured status
        res = ai_service.test_groq_connection()
        assert res["connected"] is False
        assert res["status"] == "Not configured"
        assert "not configured" in res["detail"].lower()


def test_placeholder_api_key_variants_rejected():
    """Verify various placeholder key patterns are correctly classified as unconfigured."""
    placeholders = [
        "",
        "   ",
        "your_groq_api_key",
        "gsk_placeholder_key",
        "gsk_placeholder_replace_with_actual_key",
    ]
    for ph in placeholders:
        custom_settings = Settings(GROQ_API_KEY=ph)
        assert custom_settings.is_groq_configured is False


# 2. Valid Configuration Properties Tests
def test_valid_configuration_properties():
    """Verify valid settings produce expected properties and properly mask secrets."""
    valid_settings = Settings(
        GROQ_API_KEY=DUMMY_VALID_KEY,
        GROQ_MODEL="llama-3.3-70b-versatile",
        GROQ_TEMPERATURE=0.2,
        GROQ_MAX_TOKENS=2048,
        GROQ_TIMEOUT=45.0,
    )
    assert valid_settings.is_groq_configured is True
    assert valid_settings.GROQ_MODEL == "llama-3.3-70b-versatile"
    assert valid_settings.GROQ_TEMPERATURE == 0.2
    assert valid_settings.GROQ_MAX_TOKENS == 2048
    assert valid_settings.GROQ_TIMEOUT == 45.0

    # Ensure secret masking
    masked = valid_settings.safe_groq_api_key
    assert DUMMY_VALID_KEY not in masked
    assert masked.startswith("gsk_")
    assert masked.endswith("wxyz")


# 3. Successful Mocked Client Response Tests
def test_successful_mocked_client_response():
    """Verify that a successful Groq response reports Connected status with full metadata."""
    mock_response = AIMessage(content="OK. System is operational.")

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch.object(settings, "GROQ_MODEL", "llama-3.3-70b-versatile"), \
         patch("langchain_groq.ChatGroq.invoke", return_value=mock_response):

        res = ai_service.test_groq_connection()
        assert res["connected"] is True
        assert res["status"] == "Connected"
        assert res["provider"] == "Groq"
        assert res["model"] == "llama-3.3-70b-versatile"
        assert "Successfully established live connection" in res["detail"]


# 4. Authentication Failure Tests
def test_authentication_failure():
    """Verify that Groq 401 AuthenticationError is caught and classified as Authentication failed."""
    auth_err = groq.AuthenticationError(
        "Invalid API key provided.",
        response=httpx.Response(401, request=DUMMY_HTTPX_REQ),
        body={"error": {"message": "Invalid API key"}},
    )

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch("langchain_groq.ChatGroq.invoke", side_effect=auth_err):

        res = ai_service.test_groq_connection()
        assert res["connected"] is False
        assert res["status"] == "Authentication failed"
        assert "authentication with groq api failed" in res["detail"].lower()


# 5. Model Unavailable Tests
def test_model_unavailable():
    """Verify that Groq 404 NotFoundError is caught and classified as Model unavailable."""
    not_found_err = groq.NotFoundError(
        "Model 'decommissioned-model-v1' not found.",
        response=httpx.Response(404, request=DUMMY_HTTPX_REQ),
        body={"error": {"message": "Model not found"}},
    )

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch.object(settings, "GROQ_MODEL", "decommissioned-model-v1"), \
         patch("langchain_groq.ChatGroq.invoke", side_effect=not_found_err):

        res = ai_service.test_groq_connection()
        assert res["connected"] is False
        assert res["status"] == "Model unavailable"
        assert "decommissioned-model-v1" in res["detail"]


# 6. Rate Limit Response Tests
def test_rate_limit_response():
    """Verify that Groq 429 RateLimitError is caught and classified as Rate limited."""
    rate_err = groq.RateLimitError(
        "Rate limit exceeded: TPM reached.",
        response=httpx.Response(429, request=DUMMY_HTTPX_REQ),
        body={"error": {"message": "Rate limit exceeded"}},
    )

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch("langchain_groq.ChatGroq.invoke", side_effect=rate_err):

        res = ai_service.test_groq_connection()
        assert res["connected"] is False
        assert res["status"] == "Rate limited"
        assert "rate limit exceeded" in res["detail"].lower()


# 7. Request Timeout Tests
def test_timeout_response():
    """Verify that request timeout is caught and classified as Timeout."""
    timeout_err = groq.APITimeoutError(request=DUMMY_HTTPX_REQ)

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch("langchain_groq.ChatGroq.invoke", side_effect=timeout_err):

        res = ai_service.test_groq_connection()
        assert res["connected"] is False
        assert res["status"] == "Timeout"
        assert "timed out" in res["detail"].lower()


# 8. Empty Response Tests
def test_empty_response():
    """Verify that empty or whitespace-only response content from Groq returns Unexpected error."""
    mock_empty_response = AIMessage(content="   ")

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch("langchain_groq.ChatGroq.invoke", return_value=mock_empty_response):

        res = ai_service.test_groq_connection()
        assert res["connected"] is False
        assert res["status"] == "Unexpected error"
        assert "empty response" in res["detail"].lower()


# 9. AI Health Endpoint Route Tests
def test_ai_health_endpoint_when_connected():
    """Verify GET /api/health/ai returns HTTP 200 when Groq connectivity succeeds."""
    mock_response = AIMessage(content="OK")

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch("langchain_groq.ChatGroq.invoke", return_value=mock_response):

        response = client.get("/api/health/ai")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["status"] == "Connected"
        assert data["provider"] == "Groq"
        assert DUMMY_VALID_KEY not in str(data)


def test_ai_health_endpoint_when_unconfigured():
    """Verify GET /api/health/ai returns HTTP 503 when Groq API key is unconfigured."""
    with patch.object(settings, "GROQ_API_KEY", "your_groq_api_key"):
        response = client.get("/api/health/ai")
        assert response.status_code == 503
        data = response.json()
        assert data["connected"] is False
        assert data["status"] == "Not configured"
        assert "not configured" in data["detail"].lower()


# 10. Existing Health Endpoints Independent of Groq Tests
def test_core_health_endpoints_remain_independent_of_groq():
    """Verify that GET /api/health and GET /api/health/ready continue functioning when Groq is unconfigured or failing."""
    with patch.object(settings, "GROQ_API_KEY", "your_groq_api_key"), \
         patch("app.api.routes.health.check_database_connectivity", return_value=(True, None)):

        # General application health is always 200
        health_res = client.get("/api/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "healthy"

        # Database readiness is 200 and unaffected by Groq state
        ready_res = client.get("/api/health/ready")
        assert ready_res.status_code == 200
        assert ready_res.json()["status"] == "ready"
        assert ready_res.json()["database"] == "connected"
