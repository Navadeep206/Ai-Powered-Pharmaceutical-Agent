"""Tests for Investigation Business Service."""

from datetime import date
import pytest
from app.core.exceptions import (
    InvalidInvestigationDataError,
    InvalidStatusTransitionError,
)
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationStatusEnum,
    InvestigationUpdate,
    SeverityEnum,
)
from app.services.investigation_service import investigation_service


def test_validate_valid_investigation():
    """Verify validation and normalization of valid investigation payload."""
    payload = InvestigationCreate(
        incident_title="  Temperature Excursion in Reactor R-102  ",
        incident_description="  Observed cooling glycol flow interruption during Friedel-Crafts reaction.  ",
        batch_number="  batch-9941a  ",
        severity=SeverityEnum.CRITICAL,
        incident_date=date(2026, 11, 1),
        detection_date=date(2026, 11, 2),
    )
    validated = investigation_service.validate_investigation_creation(payload)
    assert validated.incident_title == "Temperature Excursion in Reactor R-102"
    assert validated.batch_number == "batch-9941a"
    assert validated.investigation_status == InvestigationStatusEnum.OPEN


def test_date_chronology_validation():
    """Verify detection date prior to incident date is rejected."""
    payload = InvestigationCreate(
        incident_title="Anomaly in crystallizer",
        incident_description="Detailed narrative explaining anomaly in crystallizer.",
        severity=SeverityEnum.HIGH,
        incident_date=date(2026, 11, 5),
        detection_date=date(2026, 11, 1),  # Detection before incident!
    )
    with pytest.raises(InvalidInvestigationDataError):
        investigation_service.validate_investigation_creation(payload)


def test_allowed_status_transitions():
    """Verify permitted GxP investigation lifecycle transitions."""
    # Open -> Under Investigation
    investigation_service.validate_status_transition(
        InvestigationStatusEnum.OPEN,
        InvestigationStatusEnum.UNDER_INVESTIGATION,
    )
    # Under Investigation -> Pending Review
    investigation_service.validate_status_transition(
        InvestigationStatusEnum.UNDER_INVESTIGATION,
        InvestigationStatusEnum.PENDING_REVIEW,
    )
    # Pending Review -> Closed
    investigation_service.validate_status_transition(
        InvestigationStatusEnum.PENDING_REVIEW,
        InvestigationStatusEnum.CLOSED,
    )
    # Closed -> Under Investigation (Re-opening)
    investigation_service.validate_status_transition(
        InvestigationStatusEnum.CLOSED,
        InvestigationStatusEnum.UNDER_INVESTIGATION,
    )


def test_forbidden_direct_open_to_closed_transition():
    """Verify direct jump from Open to Closed is strictly prohibited."""
    with pytest.raises(InvalidStatusTransitionError) as exc_info:
        investigation_service.validate_status_transition(
            InvestigationStatusEnum.OPEN,
            InvestigationStatusEnum.CLOSED,
        )
    assert "Direct transition from 'Open' to 'Closed' is prohibited" in str(exc_info.value)


def test_prepare_investigation_response():
    """Verify response model preparation attaches compliant ID and timestamps."""
    payload = InvestigationCreate(
        incident_title="Yield deficit in API isolation",
        incident_description="Centrifuge yield dropped 12% below established historical lower limit.",
        severity=SeverityEnum.MEDIUM,
    )
    response = investigation_service.prepare_investigation_response(payload)
    assert response.investigation_id.startswith("INV-2026-")
    assert response.incident_title == payload.incident_title
    assert response.created_at is not None

