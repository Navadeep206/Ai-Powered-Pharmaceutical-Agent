"""Evidence and Gap Analysis Business Service for RootIQ.

Handles validation, categorization, and audit normalization of empirical findings,
batch record citations, analytical chromatography logs, and investigator questions.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from app.core.exceptions import InvalidEvidenceDataError
from app.core.logging import get_logger
from app.schemas.evidence import (
    EvidenceCreate,
    EvidenceResponse,
    EvidenceReviewStatusEnum,
    EvidenceTypeEnum,
)

logger = get_logger("services.evidence")


class EvidenceService:
    """Service providing evidence validation and preparation."""

    def generate_evidence_id(self) -> str:
        """Generate unique evidence identifier: EVD-XXXXX."""
        suffix = uuid.uuid4().hex[:6].upper()
        return f"EVD-{suffix}"

    def validate_evidence(self, payload: EvidenceCreate) -> EvidenceCreate:
        """Validate evidence properties, description length, and review status."""
        description = payload.description.strip() if payload.description else ""
        if len(description) < 5:
            raise InvalidEvidenceDataError(
                "Evidence description must provide at least 5 characters of technical observation detail."
            )

        source_ref = payload.source_reference.strip() if payload.source_reference else ""
        if not source_ref:
            raise InvalidEvidenceDataError(
                "Source reference citation (e.g. batch record page, SCADA log ID, SOP) is required."
            )

        if payload.evidence_type not in EvidenceTypeEnum:
            raise InvalidEvidenceDataError(
                f"Invalid evidence type '{payload.evidence_type}'. Must be one of: {[t.value for t in EvidenceTypeEnum]}."
            )

        review_status = payload.review_status or EvidenceReviewStatusEnum.PENDING_REVIEW
        if review_status not in EvidenceReviewStatusEnum:
            raise InvalidEvidenceDataError(
                f"Invalid review status '{payload.review_status}'. Must be one of: {[s.value for s in EvidenceReviewStatusEnum]}."
            )

        notes = payload.notes.strip() if payload.notes else None

        return EvidenceCreate(
            description=description,
            evidence_type=payload.evidence_type,
            source_reference=source_ref,
            review_status=review_status,
            notes=notes,
        )

    def prepare_evidence_response(
        self,
        investigation_id: str,
        validated_data: EvidenceCreate,
        evidence_id: Optional[str] = None,
    ) -> EvidenceResponse:
        """Construct a compliant EvidenceResponse object."""
        return EvidenceResponse(
            evidence_id=evidence_id or self.generate_evidence_id(),
            investigation_id=investigation_id,
            description=validated_data.description,
            evidence_type=validated_data.evidence_type,
            source_reference=validated_data.source_reference,
            review_status=validated_data.review_status or EvidenceReviewStatusEnum.PENDING_REVIEW,
            notes=validated_data.notes,
            created_at=datetime.now(timezone.utc),
        )


# Singleton service instance
evidence_service = EvidenceService()
