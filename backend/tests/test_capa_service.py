"""Tests for CAPA Business Service."""

from datetime import date
import pytest
from app.core.exceptions import (
    InvalidCAPADataError,
    InvalidCAPAStatusError,
    InvalidCAPAStatusTransitionError,
)
from app.schemas.capa import (
    CAPACreate,
    CAPAStatusEnum,
    CAPATypeEnum,
)
from app.services.capa_service import capa_service


def test_validate_valid_corrective_action():
    """Verify valid corrective action creation payload."""
    payload = CAPACreate(
        action_type=CAPATypeEnum.CORRECTIVE_ACTION,
        description="Replace torn pneumatic diaphragm in valve CV-102 actuator and perform leak test.",
        action_owner="Maintenance Engineering Lead",
        target_date=date(2026, 12, 1),
        effectiveness_verification_method="Inspect pressure retention across 5 full cycle tests.",
        related_root_cause_reference="CAUSE-01",
    )
    validated = capa_service.validate_capa_creation(payload)
    assert validated.action_type == CAPATypeEnum.CORRECTIVE_ACTION
    assert validated.status == CAPAStatusEnum.DRAFT


def test_new_capa_cannot_start_approved_or_completed():
    """Verify attempting to create a new CAPA directly as Approved or Completed is prohibited."""
    payload_approved = CAPACreate(
        action_type=CAPATypeEnum.PREVENTIVE_ACTION,
        description="Update standard operating procedure SOP-SYN-042 to include pre-shift valve check.",
        action_owner="Quality Systems Manager",
        target_date=date(2026, 12, 15),
        effectiveness_verification_method="Verify 100% training completion in LMS records.",
        status=CAPAStatusEnum.APPROVED,  # Illegal initial creation state!
    )
    with pytest.raises(InvalidCAPAStatusError) as exc_info:
        capa_service.validate_capa_creation(payload_approved)
    assert "cannot be initiated in 'Approved' status" in str(exc_info.value)

    payload_completed = CAPACreate(
        action_type=CAPATypeEnum.CORRECTIVE_ACTION,
        description="Fix the valve and close the issue right now.",
        action_owner="Lead",
        target_date=date(2026, 12, 15),
        effectiveness_verification_method="Verify operation in SCADA logs.",
        status=CAPAStatusEnum.COMPLETED,  # Illegal initial creation state!
    )
    with pytest.raises(InvalidCAPAStatusError) as exc_info:
        capa_service.validate_capa_creation(payload_completed)
    assert "cannot be initiated in 'Completed' status" in str(exc_info.value)


def test_allowed_capa_status_transitions():
    """Verify permitted CAPA workflow progression."""
    # Draft -> Proposed
    capa_service.validate_capa_status_transition(CAPAStatusEnum.DRAFT, CAPAStatusEnum.PROPOSED)
    # Proposed -> Approved
    capa_service.validate_capa_status_transition(CAPAStatusEnum.PROPOSED, CAPAStatusEnum.APPROVED)
    # Approved -> In Progress
    capa_service.validate_capa_status_transition(CAPAStatusEnum.APPROVED, CAPAStatusEnum.IN_PROGRESS)
    # In Progress -> Completed
    capa_service.validate_capa_status_transition(CAPAStatusEnum.IN_PROGRESS, CAPAStatusEnum.COMPLETED)
    # Completed -> Closed
    capa_service.validate_capa_status_transition(CAPAStatusEnum.COMPLETED, CAPAStatusEnum.CLOSED)


def test_forbidden_capa_status_transitions():
    """Verify skipping stages (e.g. Draft -> Completed, Draft -> Closed) raises error."""
    with pytest.raises(InvalidCAPAStatusTransitionError):
        capa_service.validate_capa_status_transition(CAPAStatusEnum.DRAFT, CAPAStatusEnum.COMPLETED)

    with pytest.raises(InvalidCAPAStatusTransitionError):
        capa_service.validate_capa_status_transition(CAPAStatusEnum.DRAFT, CAPAStatusEnum.CLOSED)

    with pytest.raises(InvalidCAPAStatusTransitionError):
        capa_service.validate_capa_status_transition(CAPAStatusEnum.DRAFT, CAPAStatusEnum.IN_PROGRESS)


def test_short_description_rejection():
    """Verify description under 10 chars is rejected."""
    payload = CAPACreate.model_construct(
        action_type=CAPATypeEnum.CORRECTIVE_ACTION,
        description="Short",
        action_owner="Lead",
        target_date=date(2026, 12, 1),
        effectiveness_verification_method="Valid verification method specification.",
        status=CAPAStatusEnum.DRAFT,
    )
    with pytest.raises(InvalidCAPADataError):
        capa_service.validate_capa_creation(payload)
