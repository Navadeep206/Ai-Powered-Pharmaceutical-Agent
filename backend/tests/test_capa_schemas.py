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


# --- CAPA Endpoint Integration Tests ---


def test_post_capa_endpoint():
    """Verify POST /api/investigations/{id}/capa persists CAPA in PostgreSQL."""
    inv_payload = {
        "incident_title": "Filter membrane breakthrough excursion",
        "incident_description": "Particulate counts downstream of 0.22 um filter exceeded class A limit.",
        "severity": "Critical",
        "department": "Sterile Fill",
    }
    inv_res = client.post("/api/investigations", json=inv_payload)
    inv_id = inv_res.json()["investigation_id"]

    payload = {
        "action_type": "Corrective Action",
        "description": "Recalibrate dual temperature transmitters TT-102A and TT-102B against traceable standard.",
        "action_owner": "Instrumentation Supervisor",
        "target_date": "2026-11-10",
        "effectiveness_verification_method": "Verify five-point calibration linearity with tolerance <= ±0.1°C.",
    }
    response = client.post(f"/api/investigations/{inv_id}/capa", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["investigation_id"] == inv_id
    assert data["action_owner"] == "Instrumentation Supervisor"
    assert data["status"] == "Draft"


def test_list_capa_endpoint():
    """Verify GET /api/investigations/{id}/capa returns persisted actions."""
    inv_payload = {
        "incident_title": "Packaging line blister seal integrity defect",
        "incident_description": "Leak test failures detected in 3 blisters out of 50 sampled during run.",
        "severity": "High",
        "department": "Packaging",
    }
    inv_res = client.post("/api/investigations", json=inv_payload)
    inv_id = inv_res.json()["investigation_id"]

    payload = {
        "action_type": "Preventive Action",
        "description": "Replace sealing heater cartridge elements and install thermal imaging sensor.",
        "action_owner": "Packaging Maintenance Lead",
        "target_date": "2026-12-15",
        "effectiveness_verification_method": "Execute dye penetration leak testing across 10 consecutive packaging batches.",
    }
    client.post(f"/api/investigations/{inv_id}/capa", json=payload)

    response = client.get(f"/api/investigations/{inv_id}/capa")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["action_owner"] == "Packaging Maintenance Lead"
