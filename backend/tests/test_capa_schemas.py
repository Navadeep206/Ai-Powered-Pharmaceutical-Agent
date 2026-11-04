"""Tests for Corrective and Preventive Action (CAPA) schemas and routes."""

from datetime import date
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.capa import (
    CAPACreate,
    CAPATypeEnum,
    CAPAStatusEnum,
)

client = TestClient(app)


def test_valid_capa_create():
    """Verify well-formed CAPACreate payload passes validation."""
    capa = CAPACreate(
        action_type="Corrective Action",
        description="Replace ruptured diaphragm in pneumatic regulator PR-102 and test seal integrity.",
        action_owner="Maintenance Engineering Lead",
        target_date="2026-11-15",
        effectiveness_verification_method="Execute 3 pressure cycle tests up to 6.0 bar with zero differential pressure drop.",
        related_root_cause_reference="CAUSE-01",
    )
    assert capa.action_type == CAPATypeEnum.CORRECTIVE_ACTION
    assert capa.status == CAPAStatusEnum.DRAFT  # Defaults to Draft, never auto-approved
    assert capa.target_date == date(2026, 11, 15)


def test_preventive_action_type():
    """Verify Preventive Action classification is supported."""
    capa = CAPACreate(
        action_type="Preventive Action",
        description="Establish quarterly preventive replacement schedule for all pneumatic regulator diaphragms across Synthesis unit.",
        action_owner="Quality Reliability Manager",
        target_date="2026-12-01",
        effectiveness_verification_method="Review maintenance logs after 6 months to ensure 100% adherence to replacement window.",
    )
    assert capa.action_type == CAPATypeEnum.PREVENTIVE_ACTION


def test_invalid_action_type_rejection():
    """Verify invalid CAPA action types are rejected."""
    with pytest.raises(ValidationError):
        CAPACreate(
            action_type="Immediate Fix",  # Invalid type
            description="Fixing the issue right away",
            action_owner="Lead",
            target_date="2026-11-20",
            effectiveness_verification_method="Inspect visual appearance",
        )


def test_missing_required_capa_fields():
    """Verify missing required fields raise validation errors."""
    with pytest.raises(ValidationError) as exc_info:
        CAPACreate(
            action_type="Corrective Action",
            description="Short desc",
        )
    errors = exc_info.value.errors()
    missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
    assert "action_owner" in missing_fields
    assert "target_date" in missing_fields
    assert "effectiveness_verification_method" in missing_fields


# --- CAPA Endpoint Tests ---


def test_post_capa_endpoint():
    """Verify POST /api/investigations/{id}/capa returns HTTP 501 Not Implemented."""
    payload = {
        "action_type": "Corrective Action",
        "description": "Recalibrate dual temperature transmitters TT-102A and TT-102B against traceable standard.",
        "action_owner": "Instrumentation Supervisor",
        "target_date": "2026-11-10",
        "effectiveness_verification_method": "Verify five-point calibration linearity with tolerance <= ±0.1°C.",
    }
    response = client.post("/api/investigations/INV-2026-001/capa", json=payload)
    assert response.status_code == 501
    assert "INV-2026-001" in response.json()["message"]


def test_list_capa_endpoint():
    """Verify GET /api/investigations/{id}/capa returns HTTP 501 Not Implemented."""
    response = client.get("/api/investigations/INV-2026-001/capa")
    assert response.status_code == 501
    assert "INV-2026-001" in response.json()["message"]
