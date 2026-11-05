"""Investigation Business Service for RootIQ.

Handles deviation validation, status transition rules, metadata preparation,
and sanitization adhering to ICH Q9/Q10 quality risk management principles.
"""

import random
from datetime import datetime, timezone
from typing import Optional, Set, Tuple
from app.core.exceptions import (
    InvalidInvestigationDataError,
    InvalidStatusTransitionError,
)
from app.core.logging import get_logger
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationResponse,
    InvestigationStatusEnum,
    InvestigationUpdate,
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


# Singleton service instance
investigation_service = InvestigationService()
