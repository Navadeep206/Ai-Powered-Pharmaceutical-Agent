"""Evidence and Gap Analysis Business Service for RootIQ.

Handles validation, categorization, and audit normalization of empirical findings,
batch record citations, analytical chromatography logs, and investigator questions.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.exceptions import InvalidEvidenceDataError
from app.core.logging import get_logger
from app.models.evidence import Evidence
from app.repositories.activity_repository import activity_repository
from app.repositories.evidence_repository import evidence_repository
from app.repositories.investigation_repository import investigation_repository
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


    def to_evidence_response(self, investigation_number: str, evidence: Evidence) -> EvidenceResponse:
        """Convert ORM Evidence model to EvidenceResponse schema."""
        return EvidenceResponse(
            evidence_id=str(evidence.id),
            investigation_id=investigation_number,
            description=evidence.description,
            evidence_type=evidence.evidence_type,
            source_reference=evidence.source_reference,
            review_status=evidence.review_status,
            notes=evidence.notes,
            created_at=evidence.created_at,
        )

    def create_evidence(
        self,
        db: Session,
        investigation_id: str,
        payload: EvidenceCreate,
    ) -> EvidenceResponse:
        """Validate, persist evidence in PostgreSQL, log activity, and return schema."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        validated = self.validate_evidence(payload)

        evidence_data = {
            "investigation_id": inv.id,
            "evidence_type": validated.evidence_type,
            "description": validated.description,
            "source_reference": validated.source_reference,
            "review_status": validated.review_status or EvidenceReviewStatusEnum.PENDING_REVIEW,
            "notes": validated.notes,
        }

        try:
            evidence = evidence_repository.create(db, evidence_data)
            activity_repository.create(
                db,
                {
                    "investigation_id": inv.id,
                    "activity_type": "EVIDENCE_ADDED",
                    "description": f"Evidence ({validated.evidence_type.value}) logged: {validated.description[:100]}",
                    "actor_identifier": "System",
                    "activity_metadata": {
                        "evidence_type": validated.evidence_type.value,
                        "source_reference": validated.source_reference,
                    },
                },
            )
            db.commit()
            db.refresh(evidence)
            return self.to_evidence_response(inv.investigation_number, evidence)
        except Exception:
            db.rollback()
            raise

    def list_evidence(
        self,
        db: Session,
        investigation_id: str,
    ) -> List[EvidenceResponse]:
        """Fetch all evidence items for an investigation."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        items = evidence_repository.list_by_investigation(db, inv.id)
        return [self.to_evidence_response(inv.investigation_number, item) for item in items]


# Singleton service instance
evidence_service = EvidenceService()
