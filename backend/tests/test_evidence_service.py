"""Tests for Evidence Business Service."""

import pytest
from app.core.exceptions import InvalidEvidenceDataError
from app.schemas.evidence import (
    EvidenceCreate,
    EvidenceReviewStatusEnum,
    EvidenceTypeEnum,
)
from app.services.evidence_service import evidence_service


def test_validate_valid_evidence():
    """Verify validation and normalization of evidence payload."""
    payload = EvidenceCreate(
        description="  SCADA trend log confirms coolant supply valve shut down at 14:22 UTC.  ",
        evidence_type=EvidenceTypeEnum.SUPPORTING,
        source_reference="  SCADA-TREND-20261101-R102  ",
        review_status=EvidenceReviewStatusEnum.VERIFIED,
    )
    validated = evidence_service.validate_evidence(payload)
    assert validated.description == "SCADA trend log confirms coolant supply valve shut down at 14:22 UTC."
    assert validated.source_reference == "SCADA-TREND-20261101-R102"
    assert validated.review_status == EvidenceReviewStatusEnum.VERIFIED


def test_missing_source_reference_rejection():
    """Verify evidence without source reference citation is rejected."""
    payload = EvidenceCreate(
        description="Temperature probe was calibrated within limits.",
        evidence_type=EvidenceTypeEnum.SUPPORTING,
        source_reference="   ",  # Empty
    )
    with pytest.raises(InvalidEvidenceDataError):
        evidence_service.validate_evidence(payload)


def test_too_short_description_rejection():
    """Verify evidence with brief description is rejected."""
    payload = EvidenceCreate.model_construct(
        description="Bad",  # Too short
        evidence_type=EvidenceTypeEnum.CONTRADICTORY,
        source_reference="REF-001",
        review_status=EvidenceReviewStatusEnum.PENDING_REVIEW,
    )
    with pytest.raises(InvalidEvidenceDataError):
        evidence_service.validate_evidence(payload)


def test_prepare_evidence_response():
    """Verify response construction generates EVD- ID and timestamps."""
    payload = EvidenceCreate(
        description="Spectroscopy analysis confirms no byproduct degradation in batch 9942.",
        evidence_type=EvidenceTypeEnum.SUPPORTING,
        source_reference="QC-HPLC-9942-01",
    )
    response = evidence_service.prepare_evidence_response("INV-2026-001", payload)
    assert response.evidence_id.startswith("EVD-")
    assert response.investigation_id == "INV-2026-001"
    assert response.created_at is not None
