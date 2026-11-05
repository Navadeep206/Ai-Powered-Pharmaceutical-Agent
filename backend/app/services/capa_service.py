"""Corrective and Preventive Actions (CAPA) Business Service for RootIQ.

Handles validation, lifecycle state transitions, effectiveness verification rules,
and audit controls under FDA 21 CFR Part 211 and ICH Q10 pharmaceutical quality systems.
"""

import uuid
from datetime import date, datetime, timezone
from typing import List, Optional, Set, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.exceptions import (
    InvalidCAPADataError,
    InvalidCAPAStatusError,
    InvalidCAPAStatusTransitionError,
)
from app.core.logging import get_logger
from app.models.capa import CapaAction
from app.models.rca import FishboneCause
from app.repositories.activity_repository import activity_repository
from app.repositories.capa_repository import capa_repository
from app.repositories.investigation_repository import investigation_repository
from app.schemas.capa import (
    CAPACreate,
    CAPAResponse,
    CAPAStatusEnum,
    CAPAStatusUpdate,
    CAPATypeEnum,
)

logger = get_logger("services.capa")

# Permitted CAPA lifecycle transitions
ALLOWED_CAPA_TRANSITIONS: Set[Tuple[CAPAStatusEnum, CAPAStatusEnum]] = {
    (CAPAStatusEnum.DRAFT, CAPAStatusEnum.PROPOSED),
    (CAPAStatusEnum.PROPOSED, CAPAStatusEnum.PENDING_REVIEW),
    (CAPAStatusEnum.PROPOSED, CAPAStatusEnum.APPROVED),
    (CAPAStatusEnum.PROPOSED, CAPAStatusEnum.REJECTED),
    (CAPAStatusEnum.PROPOSED, CAPAStatusEnum.DRAFT),
    (CAPAStatusEnum.PENDING_REVIEW, CAPAStatusEnum.APPROVED),
    (CAPAStatusEnum.PENDING_REVIEW, CAPAStatusEnum.REJECTED),
    (CAPAStatusEnum.PENDING_REVIEW, CAPAStatusEnum.PROPOSED),
    (CAPAStatusEnum.APPROVED, CAPAStatusEnum.IN_PROGRESS),
    (CAPAStatusEnum.IN_PROGRESS, CAPAStatusEnum.COMPLETED),
    (CAPAStatusEnum.COMPLETED, CAPAStatusEnum.CLOSED),
    (CAPAStatusEnum.COMPLETED, CAPAStatusEnum.IN_PROGRESS),  # Re-opened if verification fails
    (CAPAStatusEnum.REJECTED, CAPAStatusEnum.DRAFT),
    (CAPAStatusEnum.REJECTED, CAPAStatusEnum.PROPOSED),
}


class CAPAService:
    """Service providing CAPA validation, lifecycle gates, and audit preparation."""

    def generate_capa_id(self) -> str:
        """Generate unique CAPA identifier: CAPA-XXXXX."""
        suffix = uuid.uuid4().hex[:6].upper()
        return f"CAPA-{suffix}"

    def validate_capa_status_transition(
        self,
        current_status: CAPAStatusEnum,
        new_status: CAPAStatusEnum,
    ) -> None:
        """Enforce strict ICH Q10 CAPA progression gates."""
        if current_status == new_status:
            return

        if (current_status, new_status) not in ALLOWED_CAPA_TRANSITIONS:
            raise InvalidCAPAStatusTransitionError(
                f"Cannot transition CAPA from '{current_status.value}' to '{new_status.value}'. Must follow formal approval workflow (Draft -> Proposed -> Approved -> In Progress -> Completed -> Closed)."
            )

    def validate_capa_creation(self, payload: CAPACreate) -> CAPACreate:
        """Validate newly submitted CAPA proposal and enforce approval gates."""
        description = payload.description.strip() if payload.description else ""
        if len(description) < 10:
            raise InvalidCAPADataError(
                "CAPA description must provide at least 10 characters detailing remediation or preventive steps."
            )

        action_owner = payload.action_owner.strip() if payload.action_owner else ""
        if len(action_owner) < 2:
            raise InvalidCAPADataError("Action owner must identify a valid responsible role or individual.")

        verification_method = (
            payload.effectiveness_verification_method.strip()
            if payload.effectiveness_verification_method
            else ""
        )
        if len(verification_method) < 10:
            raise InvalidCAPADataError(
                "Effectiveness verification method must specify measurable criteria to verify non-recurrence (minimum 10 characters)."
            )

        if payload.action_type not in CAPATypeEnum:
            raise InvalidCAPADataError(
                f"Invalid action type '{payload.action_type}'. Must be 'Corrective Action' or 'Preventive Action'."
            )

        # GxP Gate: Newly proposed actions cannot be submitted directly as Approved or Completed
        status = payload.status or CAPAStatusEnum.DRAFT
        if status in (CAPAStatusEnum.APPROVED, CAPAStatusEnum.COMPLETED, CAPAStatusEnum.CLOSED):
            raise InvalidCAPAStatusError(
                f"New CAPA actions cannot be initiated in '{status.value}' status. Initial proposals must begin in 'Draft' or 'Proposed' status pending QA review."
            )

        root_cause_ref = (
            payload.related_root_cause_reference.strip()
            if payload.related_root_cause_reference
            else None
        )

        return CAPACreate(
            action_type=payload.action_type,
            description=description,
            action_owner=action_owner,
            target_date=payload.target_date,
            effectiveness_verification_method=verification_method,
            status=status,
            related_root_cause_reference=root_cause_ref,
        )

    def prepare_capa_response(
        self,
        investigation_id: str,
        validated_data: CAPACreate,
        action_id: Optional[str] = None,
    ) -> CAPAResponse:
        """Construct full CAPAResponse object."""
        now = datetime.now(timezone.utc)
        return CAPAResponse(
            action_id=action_id or self.generate_capa_id(),
            investigation_id=investigation_id,
            action_type=validated_data.action_type,
            description=validated_data.description,
            action_owner=validated_data.action_owner,
            target_date=validated_data.target_date,
            effectiveness_verification_method=validated_data.effectiveness_verification_method,
            status=validated_data.status or CAPAStatusEnum.DRAFT,
            related_root_cause_reference=validated_data.related_root_cause_reference,
            created_at=now,
            updated_at=now,
        )


    def to_capa_response(self, investigation_number: str, capa: CapaAction) -> CAPAResponse:
        """Convert ORM CapaAction model to CAPAResponse schema."""
        return CAPAResponse(
            action_id=str(capa.id),
            investigation_id=investigation_number,
            action_type=capa.action_type,
            description=capa.description,
            action_owner=capa.action_owner,
            target_date=capa.target_date,
            effectiveness_verification_method=capa.effectiveness_verification,
            status=capa.action_status,
            related_root_cause_reference=str(capa.related_root_cause_id) if capa.related_root_cause_id else None,
            created_at=capa.created_at,
            updated_at=capa.updated_at,
        )

    def create_capa(
        self,
        db: Session,
        investigation_id: str,
        payload: CAPACreate,
    ) -> CAPAResponse:
        """Validate, persist in PostgreSQL, record activity, and return CAPA response."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        validated = self.validate_capa_creation(payload)

        # Resolve root cause ID if reference is provided
        root_cause_id = None
        if validated.related_root_cause_reference:
            try:
                candidate_uuid = uuid.UUID(validated.related_root_cause_reference)
                # Verify that this cause exists in DB
                cause_exists = db.get(FishboneCause, candidate_uuid)
                if cause_exists:
                    root_cause_id = candidate_uuid
            except (ValueError, AttributeError):
                # Not a raw UUID string, could be a label or non-UUID identifier
                pass

        capa_data = {
            "investigation_id": inv.id,
            "related_root_cause_id": root_cause_id,
            "action_type": validated.action_type,
            "description": validated.description,
            "action_owner": validated.action_owner,
            "target_date": validated.target_date,
            "effectiveness_verification": validated.effectiveness_verification_method,
            "action_status": validated.status or CAPAStatusEnum.DRAFT,
        }

        try:
            capa = capa_repository.create(db, capa_data)
            activity_repository.create(
                db,
                {
                    "investigation_id": inv.id,
                    "activity_type": "CAPA_ACTION_CREATED",
                    "description": f"CAPA action ({validated.action_type.value}) created: {validated.description[:80]}",
                    "actor_identifier": "System",
                    "activity_metadata": {
                        "action_type": validated.action_type.value,
                        "owner": validated.action_owner,
                        "target_date": validated.target_date.isoformat(),
                    },
                },
            )
            db.commit()
            db.refresh(capa)
            return self.to_capa_response(inv.investigation_number, capa)
        except Exception:
            db.rollback()
            raise

    def list_capa(
        self,
        db: Session,
        investigation_id: str,
    ) -> List[CAPAResponse]:
        """Fetch all CAPA actions linked to an investigation."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        items = capa_repository.list_by_investigation(db, inv.id)
        return [self.to_capa_response(inv.investigation_number, item) for item in items]

    def update_capa_status(
        self,
        db: Session,
        investigation_id: str,
        capa_id: str,
        payload: CAPAStatusUpdate,
    ) -> CAPAResponse:
        """Apply lifecycle status change with GxP state machine verification."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        capa = capa_repository.get_by_id(db, capa_id)
        if not capa or capa.investigation_id != inv.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"CAPA action '{capa_id}' not found for investigation '{investigation_id}'.",
            )

        self.validate_capa_status_transition(capa.action_status, payload.status)

        update_data = {"action_status": payload.status}
        if payload.status in (CAPAStatusEnum.COMPLETED, CAPAStatusEnum.CLOSED) and not capa.completed_at:
            update_data["completed_at"] = datetime.now(timezone.utc)

        try:
            updated_capa = capa_repository.update(db, capa, update_data)
            activity_repository.create(
                db,
                {
                    "investigation_id": inv.id,
                    "activity_type": "CAPA_STATUS_CHANGED",
                    "description": f"CAPA {capa.id} transitioned to '{payload.status.value}'.",
                    "actor_identifier": "System",
                    "activity_metadata": {
                        "previous_status": capa.action_status.value,
                        "new_status": payload.status.value,
                        "notes": payload.notes,
                    },
                },
            )
            db.commit()
            db.refresh(updated_capa)
            return self.to_capa_response(inv.investigation_number, updated_capa)
        except Exception:
            db.rollback()
            raise


# Singleton service instance
capa_service = CAPAService()
