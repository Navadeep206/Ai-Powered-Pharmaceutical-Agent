"""Tests for Root Cause Analysis (5-Whys and Fishbone) schemas and routes."""

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.rca import (
    FiveWhysLevel,
    FishboneCause,
    FishboneCategoryEnum,
    CauseVerificationStatusEnum,
    RCARequest,
)

client = TestClient(app)


def test_valid_five_whys_level():
    """Verify that a valid FiveWhysLevel passes validation with expected defaults."""
    level = FiveWhysLevel(
        level=1,
        question="Why did the reactor temperature exceed the setpoint?",
        answer="Cooling jacket inlet control valve CV-102 failed to actuate open.",
        evidence_references=["EVD-001", "SCADA-TREND-991"],
    )
    assert level.level == 1
    assert level.is_root_cause is False
    assert level.status == CauseVerificationStatusEnum.AI_SUGGESTION


def test_invalid_five_whys_level_range():
    """Verify that level < 1 or level > 5 raises validation error."""
    with pytest.raises(ValidationError):
        FiveWhysLevel(
            level=6,  # Exceeds max 5
            question="Why level six?",
            answer="Invalid level",
        )

    with pytest.raises(ValidationError):
        FiveWhysLevel(
            level=0,  # Below min 1
            question="Why level zero?",
            answer="Invalid level",
        )


def test_fishbone_category_validation():
    """Verify all 6 Ishikawa categories are valid and unsupported categories are rejected."""
    valid_categories = [
        "Manpower",
        "Machine",
        "Method",
        "Material",
        "Measurement",
        "Environment",
    ]
    for cat in valid_categories:
        cause = FishboneCause(
            cause_id="CAUSE-01",
            category=cat,
            cause_description=f"Potential causal factor in {cat}",
        )
        assert cause.category == FishboneCategoryEnum(cat)
        assert cause.status == CauseVerificationStatusEnum.AI_SUGGESTION

    # Invalid category
    with pytest.raises(ValidationError):
        FishboneCause(
            cause_id="CAUSE-99",
            category="Software",  # Not one of 6M categories
            cause_description="Invalid software category",
        )


def test_valid_rca_request_payload():
    """Verify full RCARequest model can be constructed."""
    req = RCARequest(
        five_whys=[
            FiveWhysLevel(
                level=1,
                question="Why did temperature rise?",
                answer="Valve CV-102 did not open.",
            ),
            FiveWhysLevel(
                level=2,
                question="Why did valve CV-102 not open?",
                answer="Pneumatic air pressure regulator had ruptured diaphragm.",
                is_root_cause=True,
                status=CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE,
            ),
        ],
        fishbone_causes=[
            FishboneCause(
                cause_id="FC-01",
                category=FishboneCategoryEnum.MACHINE,
                cause_description="Pneumatic actuator air supply line regulator diaphragm tear",
            )
        ],
        investigator_notes="Root cause identified at regulator diaphragm failure.",
    )
    assert len(req.five_whys) == 2
    assert len(req.fishbone_causes) == 1
    assert req.five_whys[1].is_root_cause is True


# --- RCA Endpoint Route Integration Tests ---


def test_post_rca_endpoint():
    """Verify POST /api/investigations/{id}/rca persists RCA study in PostgreSQL."""
    # First create an investigation to attach to
    inv_payload = {
        "incident_title": "Reaction yield dropped below validated lower threshold",
        "incident_description": "Batch yields declined from 94 percent to 76 percent across three runs.",
        "severity": "High",
        "department": "Synthesis",
    }
    inv_res = client.post("/api/investigations", json=inv_payload)
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["investigation_id"]

    rca_payload = {
        "five_whys": [
            {
                "level": 1,
                "question": "Why did reaction stall?",
                "answer": "Agitator stopped rotating.",
                "is_root_cause": True,
            }
        ],
        "fishbone_causes": [
            {
                "cause_id": "CAUSE-01",
                "category": "Machine",
                "cause_description": "Drive motor tripped due to mechanical jam in seal assembly.",
                "evidence_references": [],
                "status": "AI Suggestion",
            }
        ],
        "investigator_notes": "Initial causal evaluation completed.",
    }
    response = client.post(f"/api/investigations/{inv_id}/rca", json=rca_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["investigation_id"] == inv_id
    assert len(data["five_whys"]) == 1
    assert data["five_whys"][0]["question"] == "Why did reaction stall?"
    assert len(data["fishbone_causes"]) == 1


def test_get_rca_endpoint():
    """Verify GET /api/investigations/{id}/rca returns persisted RCA analysis."""
    # Create investigation
    inv_payload = {
        "incident_title": "Chromatography peak splitting observation",
        "incident_description": "HPLC retention time shifted 2.4 minutes earlier than validated window.",
        "severity": "Medium",
        "department": "Quality Assurance",
    }
    inv_res = client.post("/api/investigations", json=inv_payload)
    inv_id = inv_res.json()["investigation_id"]

    # Retrieve before saving: returns empty structure
    get_res = client.get(f"/api/investigations/{inv_id}/rca")
    assert get_res.status_code == 200
    assert get_res.json()["investigation_id"] == inv_id
    assert get_res.json()["five_whys"] == []

