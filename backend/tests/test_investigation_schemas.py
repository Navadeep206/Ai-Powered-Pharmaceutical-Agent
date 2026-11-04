"""Tests for Investigation schemas and route validation."""

from datetime import date
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationUpdate,
    SeverityEnum,
    InvestigationStatusEnum,
)

client = TestClient(app)


def test_valid_investigation_create():
    """Verify that a well-formed InvestigationCreate model passes validation."""
    data = {
        "incident_title": "Unexpected temperature excursion during API synthesis",
        "incident_description": "Reactor R-102 temperature reached 84°C exceeding the critical limit of 78°C.",
        "deviation_id": "DEV-2026-0104",
        "batch_number": "BATCH-9941",
        "product_name": "Atorvastatin API",
        "department": "Synthesis",
        "equipment": "Reactor R-102",
        "incident_date": "2026-11-01",
        "detection_date": "2026-11-01",
        "severity": "Critical",
        "immediate_action_taken": "Reactor cooling jacket manually flushed with chilled glycol.",
        "expected_condition": "Temperature maintained at 75°C ± 3°C",
        "actual_condition": "Excursion to 84°C for 22 minutes",
        "observed_impact": "Potential thermal degradation of intermediate batch",
        "affected_process": "Step 3: Friedel-Crafts Acylation",
        "initial_observations": "Cooling valve CV-102 actuator showed intermittent air pressure loss",
    }
    obj = InvestigationCreate(**data)
    assert obj.incident_title == data["incident_title"]
    assert obj.severity == SeverityEnum.CRITICAL
    assert obj.investigation_status == InvestigationStatusEnum.OPEN
    assert obj.incident_date == date(2026, 11, 1)


def test_invalid_severity_rejection():
    """Verify that unsupported severity levels are rejected with validation errors."""
    data = {
        "incident_title": "pH anomaly in precipitation tank",
        "incident_description": "pH observed at 4.2 instead of required 6.5.",
        "severity": "Catastrophic",  # Invalid enum value
    }
    with pytest.raises(ValidationError) as exc_info:
        InvestigationCreate(**data)
    assert "severity" in str(exc_info.value)


def test_invalid_status_rejection():
    """Verify that unsupported investigation statuses are rejected."""
    data = {
        "incident_title": "Yield deficit in final crystallization",
        "incident_description": "Crystallizer yield dropped by 14% below standard acceptance criteria.",
        "severity": "High",
        "investigation_status": "Archived",  # Invalid enum value
    }
    with pytest.raises(ValidationError) as exc_info:
        InvestigationCreate(**data)
    assert "investigation_status" in str(exc_info.value)


def test_missing_required_fields_rejection():
    """Verify missing required fields (title, description, severity) raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        InvestigationCreate(incident_title="Only title provided")
    errors = exc_info.value.errors()
    missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
    assert "incident_description" in missing_fields
    assert "severity" in missing_fields


def test_short_title_rejection():
    """Verify incident title under 3 characters is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        InvestigationCreate(
            incident_title="AB",
            incident_description="Valid long description detailing the excursion.",
            severity="Low",
        )
    assert "incident_title" in str(exc_info.value)


def test_investigation_update_partial_fields():
    """Verify InvestigationUpdate permits partial fields."""
    update = InvestigationUpdate(
        severity=SeverityEnum.MEDIUM,
        investigation_status=InvestigationStatusEnum.UNDER_INVESTIGATION,
    )
    assert update.severity == SeverityEnum.MEDIUM
    assert update.investigation_status == InvestigationStatusEnum.UNDER_INVESTIGATION
    assert update.incident_title is None


# --- Endpoint Route Scaffolding Tests ---


def test_create_investigation_endpoint_valid_payload():
    """Verify POST /api/investigations with valid payload returns HTTP 501 Not Implemented."""
    payload = {
        "incident_title": "Unexpected pressure drop in filter dryer FD-04",
        "incident_description": "Nitrogen purge pressure dropped from 3.0 bar to 1.1 bar during drying.",
        "severity": "High",
        "department": "Purification",
    }
    response = client.post("/api/investigations", json=payload)
    assert response.status_code == 501
    assert "Step 03 Phase 3" in response.json()["message"]


def test_create_investigation_endpoint_validation_error():
    """Verify POST /api/investigations with invalid payload returns HTTP 422 Unprocessable Entity."""
    payload = {
        "incident_title": "No description or severity provided",
    }
    response = client.post("/api/investigations", json=payload)
    assert response.status_code == 422


def test_list_investigations_endpoint():
    """Verify GET /api/investigations returns HTTP 501 Not Implemented."""
    response = client.get("/api/investigations")
    assert response.status_code == 501
    assert "query operations" in response.json()["message"]


def test_get_investigation_by_id_endpoint():
    """Verify GET /api/investigations/{id} returns HTTP 501 Not Implemented."""
    response = client.get("/api/investigations/INV-2026-001")
    assert response.status_code == 501
    assert "INV-2026-001" in response.json()["message"]


def test_patch_investigation_endpoint():
    """Verify PATCH /api/investigations/{id} returns HTTP 501 Not Implemented."""
    payload = {"severity": "Low"}
    response = client.patch("/api/investigations/INV-2026-001", json=payload)
    assert response.status_code == 501
