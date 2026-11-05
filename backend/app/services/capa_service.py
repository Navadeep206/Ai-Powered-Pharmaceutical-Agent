"""Corrective and Preventive Actions (CAPA) Business Service for RootIQ.

Handles validation, lifecycle state transitions, effectiveness verification rules,
and audit controls under FDA 21 CFR Part 211 and ICH Q10 pharmaceutical quality systems.
"""

import uuid
from datetime import date, datetime, timezone
from typing import Optional, Set, Tuple
from app.core.exceptions import (
    InvalidCAPADataError,
    InvalidCAPAStatusError,
    InvalidCAPAStatusTransitionError,
)
from app.core.logging import get_logger
from app.schemas.capa import (
    CAPACreate,
    CAPAResponse,
    CAPAStatusEnum,
    CAPATypeEnum,
)

logger = get_logger("services.capa")

# Permitted CAPA lifecycle transitions
ALLOWED_CAPA_TRANSITIONS: Set[Tuple[CAPAStatusEnum, CAPAStatusEnum]] = {
    (CAPAStatusEnum.DRAFT, CAPAStatusEnum.PROPOSED),
    (CAPAStatusEnum.PROPOSED, CAPAStatusEnum.APPROVED),
    (CAPAStatusEnum.PROPOSED, CAPAStatusEnum.DRAFT),
    (CAPAStatusEnum.APPROVED, CAPAStatusEnum.IN_PROGRESS),
    (CAPAStatusEnum.IN_PROGRESS, CAPAStatusEnum.COMPLETED),
    (CAPAStatusEnum.COMPLETED, CAPAStatusEnum.CLOSED),
    (CAPAStatusEnum.COMPLETED, CAPAStatusEnum.IN_PROGRESS),  # Re-opened if verification fails
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


# Singleton service instance
capa_service = CAPAService()
