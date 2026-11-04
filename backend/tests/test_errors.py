"""Tests for global error handling and logging redaction."""

from fastapi.testclient import TestClient
from app.main import app
from app.core.logging import setup_logging, get_logger, SensitiveDataFilter
import logging

client = TestClient(app)


def test_404_structured_error():
    """Verify that a nonexistent route returns a structured JSON error response."""
    response = client.get("/api/nonexistent-route-for-testing")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "HTTPException"
    assert data["status_code"] == 404
    assert "message" in data


def test_sensitive_data_filter():
    """Verify that sensitive patterns are scrubbed from log messages."""
    filter_instance = SensitiveDataFilter()
    
    # Test Groq API key scrubbing
    record1 = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py", lineno=1,
        msg="Connecting with key gsk_abcdef1234567890", args=(), exc_info=None
    )
    filter_instance.filter(record1)
    assert "gsk_abcdef" not in record1.msg
    assert "gsk_***REDACTED***" in record1.msg

    # Test Bearer token scrubbing
    record2 = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py", lineno=2,
        msg="Authorization: Bearer my_secret_token_12345", args=(), exc_info=None
    )
    filter_instance.filter(record2)
    assert "my_secret_token_12345" not in record2.msg
    assert "***REDACTED***" in record2.msg


def test_idempotent_logging_setup():
    """Verify setup_logging does not duplicate handlers when invoked repeatedly."""
    setup_logging()
    logger = logging.getLogger("rootiq")
    initial_count = len(logger.handlers)
    setup_logging()
    assert len(logger.handlers) == initial_count

