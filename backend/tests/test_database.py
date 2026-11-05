"""Tests for PostgreSQL Database Engine, Session Management, and Readiness Probes."""

from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import Settings
from app.database.connection import check_database_connectivity, get_database_status
from app.database.session import Base, SessionLocal, engine, get_db

client = TestClient(app)


def test_database_engine_configuration():
    """Verify that SQLAlchemy 2.0 engine is created centrally with pre-ping enabled."""
    assert isinstance(engine, Engine)
    assert engine.pool._pre_ping is True


def test_safe_database_url_masking():
    """Verify that safe_database_url masks passwords and keeps credentials private."""
    settings_with_password = Settings(
        DATABASE_URL="postgresql+psycopg://db_admin:super_secret_pw@localhost:5432/rootiq_db"
    )
    assert "super_secret_pw" not in settings_with_password.safe_database_url
    assert "db_admin:***@localhost:5432" in settings_with_password.safe_database_url


def test_session_local_factory():
    """Verify SessionLocal produces valid SQLAlchemy sessions and can be cleanly closed."""
    session = SessionLocal()
    try:
        assert isinstance(session, Session)
    finally:
        session.close()


def test_declarative_base():
    """Verify DeclarativeBase metadata is present."""
    assert hasattr(Base, "metadata")


def test_get_db_session_lifecycle():
    """Verify get_db generator yields an open session and closes it upon exit."""
    generator = get_db()
    session = next(generator)
    assert isinstance(session, Session)
    # Complete generator lifecycle
    with pytest.raises(StopIteration):
        next(generator)


def test_check_database_connectivity_live_or_mocked():
    """Verify connection check returns boolean and optional string tuple without raising."""
    is_connected, error_msg = check_database_connectivity()
    assert isinstance(is_connected, bool)
    if is_connected:
        assert error_msg is None
    else:
        assert isinstance(error_msg, str)
        # Verify no credentials leaked
        assert "password" not in error_msg.lower()


def test_check_database_connectivity_failure_handling():
    """Verify connection check returns clean failure when pointing to an unreachable port."""
    unreachable_engine = create_engine(
        "postgresql+psycopg://localhost:54399/nonexistent_db",
        connect_args={"connect_timeout": 1},
    )
    is_connected, error_msg = check_database_connectivity(unreachable_engine)
    assert is_connected is False
    assert error_msg is not None
    assert "Database connectivity failed" in error_msg


def test_get_database_status_structure():
    """Verify get_database_status returns structured dictionary."""
    status_data = get_database_status()
    assert "connected" in status_data
    assert status_data["database"] == "postgresql"
    assert "pool" in status_data


def test_basic_health_remains_independent_of_database():
    """Verify GET /api/health returns 200 OK regardless of database state."""
    # Mock check_database_connectivity to simulate dead database
    with patch("app.api.routes.health.check_database_connectivity", return_value=(False, "Database down")):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


def test_readiness_endpoint_success():
    """Verify GET /api/health/ready returns 200 when database connectivity succeeds."""
    with patch("app.api.routes.health.check_database_connectivity", return_value=(True, None)):
        response = client.get("/api/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"


def test_readiness_endpoint_503_when_database_unavailable():
    """Verify GET /api/health/ready returns 503 Service Unavailable when database is unreachable."""
    with patch("app.api.routes.health.check_database_connectivity", return_value=(False, "Database connection refused.")):
        response = client.get("/api/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["database"] == "disconnected"
        assert "password" not in str(data).lower()
