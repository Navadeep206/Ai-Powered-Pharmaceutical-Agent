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


# --- Endpoint Route Integration Tests ---


def test_create_investigation_endpoint_valid_payload():
    """Verify POST /api/investigations with valid payload persists and returns HTTP 201 Created."""
    payload = {
        "incident_title": "Unexpected pressure drop in filter dryer FD-04",
        "incident_description": "Nitrogen purge pressure dropped from 3.0 bar to 1.1 bar during drying.",
        "severity": "High",
        "department": "Purification",
    }
    response = client.post("/api/investigations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["incident_title"] == payload["incident_title"]
    assert data["investigation_id"].startswith("INV-")
    assert data["investigation_status"] == "Open"


def test_create_investigation_endpoint_validation_error():
    """Verify POST /api/investigations with invalid payload returns HTTP 422 Unprocessable Entity."""
    payload = {
        "incident_title": "No description or severity provided",
    }
    response = client.post("/api/investigations", json=payload)
    assert response.status_code == 422


def test_list_investigations_endpoint():
    """Verify GET /api/investigations returns HTTP 200 with paginated items."""
    response = client.get("/api/investigations")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "pagination" in data
    assert data["pagination"]["page"] == 1


def test_get_investigation_by_id_endpoint():
    """Verify GET /api/investigations/{id} returns HTTP 200 for created record and 404 for unknown."""
    # Create an investigation first
    create_payload = {
        "incident_title": "Temperature anomaly in reactor R-201",
        "incident_description": "Exothermic spike exceeded 65C during slow reagent addition step.",
        "severity": "Critical",
        "department": "Synthesis",
    }
    create_res = client.post("/api/investigations", json=create_payload)
    assert create_res.status_code == 201
    inv_id = create_res.json()["investigation_id"]

    # Retrieve by ID
    get_res = client.get(f"/api/investigations/{inv_id}")
    assert get_res.status_code == 200
    assert get_res.json()["investigation_id"] == inv_id

    # Retrieve non-existent
    unknown_res = client.get("/api/investigations/INV-UNKNOWN-9999")
    assert unknown_res.status_code == 404


def test_patch_investigation_endpoint():
    """Verify PATCH /api/investigations/{id} applies partial update."""
    create_payload = {
        "incident_title": "Agitator speed deviation in crystallizer CR-01",
        "incident_description": "Impeller RPM dropped from 120 to 45 due to electrical surge.",
        "severity": "Medium",
        "department": "Crystallization",
    }
    create_res = client.post("/api/investigations", json=create_payload)
    assert create_res.status_code == 201
    inv_id = create_res.json()["investigation_id"]

    # Patch with valid transition to Under Investigation
    patch_payload = {
        "investigation_status": "Under Investigation",
        "observed_impact": "Crystal size distribution was broadened but within release spec.",
    }
    patch_res = client.patch(f"/api/investigations/{inv_id}", json=patch_payload)
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["investigation_status"] == "Under Investigation"
    assert data["observed_impact"] == patch_payload["observed_impact"]

