"""Tests for RCA Business Service."""

import pytest
from app.core.exceptions import (
    InvalidFiveWhysStructureError,
    InvalidRCACauseStatusError,
)
from app.schemas.rca import (
    CauseVerificationStatusEnum,
    FishboneCategoryEnum,
    FishboneCause,
    FiveWhysLevel,
    RCARequest,
)
from app.services.rca_service import rca_service


def test_validate_valid_five_whys_chain():
    """Verify valid sequential 5-Whys chain passes validation."""
    levels = [
        FiveWhysLevel(level=1, question="Why did temperature rise?", answer="Cooling valve CV-102 failed to open."),
        FiveWhysLevel(level=2, question="Why did valve fail to open?", answer="Air pressure lost to pneumatic actuator."),
        FiveWhysLevel(
            level=3,
            question="Why was air pressure lost?",
            answer="Regulator diaphragm tore due to fatigue.",
            is_root_cause=True,
            status=CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE,
        ),
    ]
    validated = rca_service.validate_five_whys(levels)
    assert len(validated) == 3
    assert validated[2].is_root_cause is True


def test_non_sequential_five_whys_rejection():
    """Verify non-sequential Why numbering raises InvalidFiveWhysStructureError."""
    levels = [
        FiveWhysLevel(level=1, question="Why?", answer="Because."),
        FiveWhysLevel(level=3, question="Why?", answer="Because."),  # Skipped level 2!
    ]
    with pytest.raises(InvalidFiveWhysStructureError) as exc_info:
        rca_service.validate_five_whys(levels)
    assert "Expected level 2" in str(exc_info.value)


def test_exceeding_five_levels_rejection():
    """Verify more than 5 levels raises error."""
    levels = [
        FiveWhysLevel.model_construct(level=i + 1, question=f"Why {i+1}?", answer="Because.")
        for i in range(6)
    ]
    with pytest.raises(InvalidFiveWhysStructureError):
        rca_service.validate_five_whys(levels)


def test_root_cause_must_be_terminal_node():
    """Verify root cause designated in middle of chain raises error."""
    levels = [
        FiveWhysLevel(level=1, question="Why?", answer="Because.", is_root_cause=True),  # Designated at level 1
        FiveWhysLevel(level=2, question="Why?", answer="Because."),  # But continued!
    ]
    with pytest.raises(InvalidFiveWhysStructureError) as exc_info:
        rca_service.validate_five_whys(levels)
    assert "must be the terminal step" in str(exc_info.value)


def test_confirmed_cause_requires_evidence():
    """Verify that confirming a Fishbone cause without evidence citation raises an error."""
    causes = [
        FishboneCause(
            cause_id="FC-01",
            category=FishboneCategoryEnum.MACHINE,
            cause_description="Regulator diaphragm tear",
            status=CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE,
            evidence_references=[],  # No evidence!
        )
    ]
    with pytest.raises(InvalidRCACauseStatusError) as exc_info:
        rca_service.validate_fishbone_causes(causes)
    assert "without citing supporting evidence references" in str(exc_info.value)


def test_confirmed_cause_with_evidence_passes():
    """Verify confirmed Fishbone cause with evidence passes validation."""
    causes = [
        FishboneCause(
            cause_id="FC-01",
            category=FishboneCategoryEnum.MACHINE,
            cause_description="Regulator diaphragm tear",
            status=CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE,
            evidence_references=["EVD-001", "MAINT-LOG-992"],
        )
    ]
    validated = rca_service.validate_fishbone_causes(causes)
    assert len(validated) == 1
    assert validated[0].status == CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE
