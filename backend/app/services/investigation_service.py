"""Investigation Business Service for RootIQ.

Handles deviation validation, status transition rules, metadata preparation,
and sanitization adhering to ICH Q9/Q10 quality risk management principles.
"""

import math
import random
import uuid
from datetime import datetime, timezone
from typing import Optional, Set, Tuple
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.exceptions import (
    InvalidInvestigationDataError,
    InvalidStatusTransitionError,
)
from app.core.logging import get_logger
from app.models.investigation import Investigation
from app.repositories.activity_repository import activity_repository
from app.repositories.investigation_repository import investigation_repository
from app.schemas.common import PaginationMetadata
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationListResponse,
    InvestigationResponse,
    InvestigationStatusEnum,
    InvestigationUpdate,
    SeverityEnum,
)

logger = get_logger("services.investigation")

# Permitted GxP investigation state transitions
ALLOWED_STATUS_TRANSITIONS: Set[Tuple[InvestigationStatusEnum, InvestigationStatusEnum]] = {
    # Open deviations proceed into active investigation
    (InvestigationStatusEnum.OPEN, InvestigationStatusEnum.UNDER_INVESTIGATION),
    # Deviations under investigation can be escalated to QA review or paused back to open
    (InvestigationStatusEnum.UNDER_INVESTIGATION, InvestigationStatusEnum.PENDING_REVIEW),
    (InvestigationStatusEnum.UNDER_INVESTIGATION, InvestigationStatusEnum.OPEN),
    # Pending review can be closed by QA, or kicked back for further investigation
    (InvestigationStatusEnum.PENDING_REVIEW, InvestigationStatusEnum.CLOSED),
    (InvestigationStatusEnum.PENDING_REVIEW, InvestigationStatusEnum.UNDER_INVESTIGATION),
    # Closed deviations can be reopened into active investigation if new evidence emerges
    (InvestigationStatusEnum.CLOSED, InvestigationStatusEnum.UNDER_INVESTIGATION),
}


class InvestigationService:
    """Service providing core business validation and lifecycle progression for investigations."""

    def generate_investigation_id(self) -> str:
        """Generate a compliant deviation tracking ID format: INV-YYYY-XXXX."""
        year = datetime.now(timezone.utc).year
        suffix = random.randint(1000, 9999)
        return f"INV-{year}-{suffix}"

    def validate_dates(self, incident_date, detection_date) -> None:
        """Ensure chronological validity: an anomaly cannot be detected before it occurred."""
        if incident_date and detection_date and detection_date < incident_date:
            raise InvalidInvestigationDataError(
                f"Detection date ({detection_date}) cannot be earlier than incident date ({incident_date})."
            )

    def normalize_string(self, value: Optional[str]) -> Optional[str]:
        """Strip and normalize optional string attributes."""
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None

    def validate_status_transition(
        self,
        current_status: InvestigationStatusEnum,
        new_status: InvestigationStatusEnum,
    ) -> None:
        """Enforce strict GxP investigation lifecycle state machine transitions."""
        if current_status == new_status:
            return

        if (current_status, new_status) not in ALLOWED_STATUS_TRANSITIONS:
            # Special explanation for skipping straight to closed
            if current_status == InvestigationStatusEnum.OPEN and new_status == InvestigationStatusEnum.CLOSED:
                raise InvalidStatusTransitionError(
                    "Direct transition from 'Open' to 'Closed' is prohibited. An investigation must undergo formal RCA ('Under Investigation') and QA review ('Pending Review') before closure."
                )
            raise InvalidStatusTransitionError(
                f"Invalid lifecycle transition from '{current_status.value}' to '{new_status.value}'."
            )

    def validate_investigation_creation(
        self,
        payload: InvestigationCreate,
    ) -> InvestigationCreate:
        """Validate and normalize creation payload according to pharmaceutical quality rules."""
        # Validate dates
        self.validate_dates(payload.incident_date, payload.detection_date)

        # Normalize strings
        cleaned_title = payload.incident_title.strip()
        cleaned_description = payload.incident_description.strip()

        if len(cleaned_title) < 3:
            raise InvalidInvestigationDataError("Incident title must be at least 3 characters.")
        if len(cleaned_description) < 10:
            raise InvalidInvestigationDataError(
                "Incident narrative must provide at least 10 characters of descriptive technical detail."
            )

        # Return a normalized copy
        return InvestigationCreate(
            incident_title=cleaned_title,
            incident_description=cleaned_description,
            deviation_id=self.normalize_string(payload.deviation_id),
            batch_number=self.normalize_string(payload.batch_number),
            product_name=self.normalize_string(payload.product_name),
            department=self.normalize_string(payload.department),
            equipment=self.normalize_string(payload.equipment),
            incident_date=payload.incident_date,
            detection_date=payload.detection_date,
            severity=payload.severity,
            immediate_action_taken=self.normalize_string(payload.immediate_action_taken),
            expected_condition=self.normalize_string(payload.expected_condition),
            actual_condition=self.normalize_string(payload.actual_condition),
            observed_impact=self.normalize_string(payload.observed_impact),
            affected_process=self.normalize_string(payload.affected_process),
            initial_observations=self.normalize_string(payload.initial_observations),
            investigation_status=payload.investigation_status or InvestigationStatusEnum.OPEN,
        )

    def validate_investigation_update(
        self,
        current_status: InvestigationStatusEnum,
        update_data: InvestigationUpdate,
        existing_incident_date=None,
        existing_detection_date=None,
    ) -> InvestigationUpdate:
        """Validate partial modifications and lifecycle status shifts."""
        # Status transition check
        if update_data.investigation_status:
            self.validate_status_transition(current_status, update_data.investigation_status)

        # Date consistency check
        incident_date = update_data.incident_date or existing_incident_date
        detection_date = update_data.detection_date or existing_detection_date
        self.validate_dates(incident_date, detection_date)

        # Clean string fields if provided
        return InvestigationUpdate(
            incident_title=self.normalize_string(update_data.incident_title),
            incident_description=self.normalize_string(update_data.incident_description),
            deviation_id=self.normalize_string(update_data.deviation_id),
            batch_number=self.normalize_string(update_data.batch_number),
            product_name=self.normalize_string(update_data.product_name),
            department=self.normalize_string(update_data.department),
            equipment=self.normalize_string(update_data.equipment),
            incident_date=update_data.incident_date,
            detection_date=update_data.detection_date,
            severity=update_data.severity,
            immediate_action_taken=self.normalize_string(update_data.immediate_action_taken),
            expected_condition=self.normalize_string(update_data.expected_condition),
            actual_condition=self.normalize_string(update_data.actual_condition),
            observed_impact=self.normalize_string(update_data.observed_impact),
            affected_process=self.normalize_string(update_data.affected_process),
            initial_observations=self.normalize_string(update_data.initial_observations),
            investigation_status=update_data.investigation_status,
        )

    def prepare_investigation_response(
        self,
        validated_data: InvestigationCreate,
        investigation_id: Optional[str] = None,
    ) -> InvestigationResponse:
        """Construct a complete InvestigationResponse object."""
        now = datetime.now(timezone.utc)
        return InvestigationResponse(
            investigation_id=investigation_id or self.generate_investigation_id(),
            incident_title=validated_data.incident_title,
            incident_description=validated_data.incident_description,
            deviation_id=validated_data.deviation_id,
            batch_number=validated_data.batch_number,
            product_name=validated_data.product_name,
            department=validated_data.department,
            equipment=validated_data.equipment,
            incident_date=validated_data.incident_date,
            detection_date=validated_data.detection_date,
            severity=validated_data.severity,
            immediate_action_taken=validated_data.immediate_action_taken,
            expected_condition=validated_data.expected_condition,
            actual_condition=validated_data.actual_condition,
            observed_impact=validated_data.observed_impact,
            affected_process=validated_data.affected_process,
            initial_observations=validated_data.initial_observations,
            investigation_status=validated_data.investigation_status or InvestigationStatusEnum.OPEN,
            created_at=now,
            updated_at=now,
        )


    def to_investigation_response(self, inv: Investigation) -> InvestigationResponse:
        """Serialize SQLAlchemy model to InvestigationResponse schema."""
        return InvestigationResponse(
            investigation_id=inv.investigation_number,
            incident_title=inv.incident_title,
            incident_description=inv.incident_description,
            deviation_id=inv.deviation_id,
            batch_number=inv.batch_number,
            product_name=inv.product_name,
            department=inv.department,
            equipment=inv.equipment,
            incident_date=inv.incident_date,
            detection_date=inv.detection_date,
            severity=inv.severity,
            immediate_action_taken=inv.immediate_action_taken,
            expected_condition=inv.expected_condition,
            actual_condition=inv.actual_condition,
            observed_impact=inv.observed_impact,
            affected_process=inv.affected_process,
            initial_observations=inv.initial_observations,
            investigation_status=inv.investigation_status,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )

    def generate_unique_investigation_number(self, db: Session) -> str:
        """Generate a guaranteed unique human-readable tracking ID: INV-YYYY-XXXX."""
        year = datetime.now(timezone.utc).year
        for _ in range(100):
            suffix = random.randint(1000, 9999)
            candidate = f"INV-{year}-{suffix}"
            if not investigation_repository.get_by_number(db, candidate):
                return candidate
        return f"INV-{year}-{uuid.uuid4().hex[:6].upper()}"

    def create_investigation(
        self,
        db: Session,
        payload: InvestigationCreate,
    ) -> InvestigationResponse:
        """Validate, persist in PostgreSQL, record activity, and return response."""
        validated = self.validate_investigation_creation(payload)
        inv_number = self.generate_unique_investigation_number(db)

        inv_data = {
            "investigation_number": inv_number,
            "incident_title": validated.incident_title,
            "incident_description": validated.incident_description,
            "deviation_id": validated.deviation_id,
            "batch_number": validated.batch_number,
            "product_name": validated.product_name,
            "department": validated.department,
            "equipment": validated.equipment,
            "incident_date": validated.incident_date,
            "detection_date": validated.detection_date,
            "severity": validated.severity,
            "immediate_action_taken": validated.immediate_action_taken,
            "expected_condition": validated.expected_condition,
            "actual_condition": validated.actual_condition,
            "observed_impact": validated.observed_impact,
            "affected_process": validated.affected_process,
            "initial_observations": validated.initial_observations,
            "investigation_status": validated.investigation_status or InvestigationStatusEnum.OPEN,
        }

        try:
            inv = investigation_repository.create(db, inv_data)
            activity_repository.create(
                db,
                {
                    "investigation_id": inv.id,
                    "activity_type": "INVESTIGATION_CREATED",
                    "description": f"Quality deviation {inv.investigation_number} registered: {inv.incident_title}",
                    "actor_identifier": "System",
                    "activity_metadata": {
                        "severity": inv.severity.value,
                        "department": inv.department,
                        "batch_number": inv.batch_number,
                    },
                },
            )
            db.commit()
            db.refresh(inv)
            return self.to_investigation_response(inv)
        except IntegrityError as err:
            db.rollback()
            logger.warning("Uniqueness conflict creating investigation: %s", err)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An investigation with number '{inv_number}' or conflicting unique key already exists.",
            )
        except Exception:
            db.rollback()
            raise

    def get_investigation(self, db: Session, identifier: str) -> InvestigationResponse:
        """Retrieve an investigation by UUID or investigation_number, or 404."""
        inv = investigation_repository.get_by_id(db, identifier)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{identifier}' not found.",
            )
        return self.to_investigation_response(inv)

    def list_investigations(
        self,
        db: Session,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        status_filter: Optional[InvestigationStatusEnum] = None,
        severity: Optional[SeverityEnum] = None,
        department: Optional[str] = None,
    ) -> InvestigationListResponse:
        """Query paginated investigations with full filtering support."""
        items, total = investigation_repository.list_paginated(
            db=db,
            page=page,
            page_size=limit,
            search=search,
            status=status_filter,
            severity=severity,
            department=department,
        )
        total_pages = math.ceil(total / limit) if limit > 0 else 0
        has_next = page < total_pages
        has_prev = page > 1

        pagination = PaginationMetadata(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        )

        return InvestigationListResponse(
            items=[self.to_investigation_response(i) for i in items],
            pagination=pagination,
        )

    def update_investigation(
        self,
        db: Session,
        identifier: str,
        payload: InvestigationUpdate,
    ) -> InvestigationResponse:
        """Apply partial update to an existing investigation adhering to state machine transitions."""
        inv = investigation_repository.get_by_id(db, identifier)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{identifier}' not found.",
            )

        validated = self.validate_investigation_update(
            current_status=inv.investigation_status,
            update_data=payload,
            existing_incident_date=inv.incident_date,
            existing_detection_date=inv.detection_date,
        )

        update_dict = validated.model_dump(exclude_unset=True)
        # If status changed to CLOSED, record closed_at
        if (
            "investigation_status" in update_dict
            and update_dict["investigation_status"] == InvestigationStatusEnum.CLOSED
            and inv.investigation_status != InvestigationStatusEnum.CLOSED
        ):
            update_dict["closed_at"] = datetime.now(timezone.utc)

        try:
            updated_inv = investigation_repository.update(db, inv, update_dict)
            activity_repository.create(
                db,
                {
                    "investigation_id": inv.id,
                    "activity_type": "INVESTIGATION_UPDATED",
                    "description": f"Investigation {inv.investigation_number} details updated.",
                    "actor_identifier": "System",
                    "activity_metadata": {"updated_fields": list(update_dict.keys())},
                },
            )
            db.commit()
            db.refresh(updated_inv)
            return self.to_investigation_response(updated_inv)
        except Exception:
            db.rollback()
            raise


# Singleton service instance
investigation_service = InvestigationService()
