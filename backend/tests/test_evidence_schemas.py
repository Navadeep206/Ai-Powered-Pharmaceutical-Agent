"""Tests for Evidence schemas and routes."""

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.evidence import (
    EvidenceCreate,
    EvidenceTypeEnum,
    EvidenceReviewStatusEnum,
)

client = TestClient(app)


def test_valid_evidence_create():
    """Verify well-formed EvidenceCreate payload passes validation."""
    item = EvidenceCreate(
        description="SCADA trend log shows cooling water flow dropped to 0 L/min at 14:22 UTC.",
        evidence_type="Supporting",
        source_reference="SCADA-LOG-20261101-R102",
        review_status="Verified",
        notes="Corroborated by physical inspection of actuator.",
    )
    assert item.evidence_type == EvidenceTypeEnum.SUPPORTING
    assert item.review_status == EvidenceReviewStatusEnum.VERIFIED


def test_evidence_type_variants():
    """Verify all 4 evidence types are supported."""
    types = [
        "Supporting",
        "Contradictory",
        "Missing Evidence",
        "Investigator Question",
    ]
    for et in types:
        item = EvidenceCreate(
            description="Testing evidence variant specification",
            evidence_type=et,
            source_reference="REF-001",
        )
        assert item.evidence_type == EvidenceTypeEnum(et)


def test_invalid_evidence_type_rejection():
    """Verify unsupported evidence types are rejected."""
    with pytest.raises(ValidationError):
        EvidenceCreate(
            description="Testing invalid evidence category",
            evidence_type="Hearsay",  # Invalid
            source_reference="REF-001",
        )


def test_short_description_rejection():
    """Verify description under 5 characters raises validation error."""
    with pytest.raises(ValidationError):
        EvidenceCreate(
            description="Tiny",  # Too short
            evidence_type="Supporting",
            source_reference="REF-001",
        )


# --- Evidence Endpoint Tests ---


def test_post_evidence_endpoint():
    """Verify POST /api/investigations/{id}/evidence returns HTTP 501 Not Implemented."""
    payload = {
        "description": "Temperature probe calibration record Cal-2026-09 confirms probe was within spec.",
        "evidence_type": "Supporting",
        "source_reference": "QC-CAL-2026-09",
    }
    response = client.post("/api/investigations/INV-2026-001/evidence", json=payload)
    assert response.status_code == 501
    assert "INV-2026-001" in response.json()["message"]


def test_list_evidence_endpoint():
    """Verify GET /api/investigations/{id}/evidence returns HTTP 501 Not Implemented."""
    response = client.get("/api/investigations/INV-2026-001/evidence")
    assert response.status_code == 501
    assert "INV-2026-001" in response.json()["message"]

