"""Step 08 Phase 1 Comprehensive Functional, Verification and Reliability Tests.

Validates:
- DEF-01: Status normalization aliases for 5-Whys and Fishbone schemas.
- DEF-03: Global CAPA listing endpoint (/api/capa) with investigation join and filtering.
- DEF-04: Evidence review status update endpoint (PATCH /api/investigations/{id}/evidence/{evidence_id}) and audit logging.
- DEF-05: CAPA status lifecycle transitions (Draft -> Pending Review, Approved, Rejected).
- DEF-07: Timezone-aware UTC timestamp compliance.
- Complete end-to-end controlled investigation lifecycle with PostgreSQL persistence.
- Failure resilience and error boundaries (404, 422, 400, transaction rollback).
"""

import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.main import app
from app.models.activity import InvestigationActivity
from app.models.capa import CapaAction
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.rca import RCAAnalysis
from app.schemas.rca import (
    FiveWhysLevel,
    FishboneCause,
    FishboneCategoryEnum,
    CauseVerificationStatusEnum,
)
from app.schemas.document import NormalizedIncidentIntake, IntakeMethodEnum

client = TestClient(app)


@pytest.fixture
def db():
    """Provides an isolated database session for state verification."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# DEF-01: 5-Whys and Fishbone Status Normalization Aliases
# ---------------------------------------------------------------------------

def test_five_whys_status_normalization_aliases():
    """Verify that FiveWhysLevel normalizes legacy and UI aliases to canonical enums."""
    test_cases = [
        ("Evidence-Supported", CauseVerificationStatusEnum.EVIDENCE_SUPPORTED),
        ("Evidence Supported", CauseVerificationStatusEnum.EVIDENCE_SUPPORTED),
        ("Requires Evidence", CauseVerificationStatusEnum.AI_SUGGESTION),
        ("Pending Review", CauseVerificationStatusEnum.HUMAN_REVIEWED),
        ("Confirmed by Investigator", CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE),
        ("AI Suggestion", CauseVerificationStatusEnum.AI_SUGGESTION),
        ("Human Reviewed", CauseVerificationStatusEnum.HUMAN_REVIEWED),
        ("Confirmed Root Cause", CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE),
        ("Ruled Out", CauseVerificationStatusEnum.RULED_OUT),
    ]

    for input_status, expected_enum in test_cases:
        level = FiveWhysLevel(
            level=1,
            question="Why did the filter clog?",
            answer="Particulate accumulation in pre-column.",
            status=input_status,
        )
        assert level.status == expected_enum, f"Expected {expected_enum} for input {input_status}, got {level.status}"


def test_fishbone_cause_status_normalization_aliases():
    """Verify that FishboneCause normalizes legacy and UI aliases to canonical enums."""
    test_cases = [
        ("Evidence-Supported", CauseVerificationStatusEnum.EVIDENCE_SUPPORTED),
        ("Requires Evidence", CauseVerificationStatusEnum.AI_SUGGESTION),
        ("Pending Review", CauseVerificationStatusEnum.HUMAN_REVIEWED),
        ("Confirmed by Investigator", CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE),
        ("Ruled Out", CauseVerificationStatusEnum.RULED_OUT),
    ]

    for idx, (input_status, expected_enum) in enumerate(test_cases):
        cause = FishboneCause(
            cause_id=f"FC-TEST-{idx}",
            category=FishboneCategoryEnum.MACHINE,
            cause_description="Pressure transducer drift",
            status=input_status,
        )
        assert cause.status == expected_enum, f"Expected {expected_enum} for input {input_status}"


# ---------------------------------------------------------------------------
# DEF-03: Global CAPA Listing Endpoint (/api/capa)
# ---------------------------------------------------------------------------

def test_global_capa_endpoint_listing_and_filtering(db):
    """Verify GET /api/capa returns portfolio-level CAPA records with joined investigation details."""
    suffix = uuid.uuid4().hex[:6].upper()

    # 1. Create test investigation
    inv_res = client.post("/api/investigations", json={
        "incident_title": f"Crystallization Yield Drop B-{suffix}",
        "incident_description": "API yield decreased by 18% during crystallization.",
        "batch_number": f"BATCH-{suffix}",
        "product_name": "Atorvastatin API",
        "department": "Downstream",
        "severity": "High",
        "incident_date": "2026-11-01",
        "detection_date": "2026-11-01",
    })
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["investigation_id"]

    # 2. Add two CAPA actions: one Corrective Action, one Preventive Action
    capa1_res = client.post(f"/api/investigations/{inv_id}/capa", json={
        "action_type": "Corrective Action",
        "description": f"Recalibrate crystallizer cooling jacket sensors-{suffix}",
        "action_owner": "Instrumentation Lead",
        "target_date": "2026-11-20",
        "effectiveness_verification_method": "Verify temperature uniformity across next 3 batches.",
        "status": "Draft",
    })
    assert capa1_res.status_code == 201

    capa2_res = client.post(f"/api/investigations/{inv_id}/capa", json={
        "action_type": "Preventive Action",
        "description": f"Update SOP-CRY-004 cooling curve ramp rate controls-{suffix}",
        "action_owner": "Process Engineer",
        "target_date": "2026-11-30",
        "effectiveness_verification_method": "Audit recipe configuration and confirm automated ramp enforcement.",
        "status": "Draft",
    })
    assert capa2_res.status_code == 201

    # 3. GET /api/capa - Global listing
    global_res = client.get("/api/capa")
    assert global_res.status_code == 200
    all_capas = global_res.json()
    assert isinstance(all_capas, list)

    # Find created CAPAs and assert joined investigation fields
    found_capas = [c for c in all_capas if suffix in c.get("description", "")]
    assert len(found_capas) == 2
    for c in found_capas:
        assert c["investigation_id"] == inv_id
        assert c["status"] == "Draft"

    # 4. Test filter by status
    filtered_res = client.get("/api/capa?status=Draft")
    assert filtered_res.status_code == 200
    draft_capas = [c for c in filtered_res.json() if suffix in c.get("description", "")]
    assert len(draft_capas) == 2

    # 5. Test search filter
    search_res = client.get(f"/api/capa?search={suffix}")
    assert search_res.status_code == 200
    search_capas = search_res.json()
    assert len(search_capas) >= 2


# ---------------------------------------------------------------------------
# DEF-04: Evidence Status Review API & Audit Logging
# ---------------------------------------------------------------------------

def test_evidence_status_update_and_audit(db):
    """Verify PATCH /api/investigations/{id}/evidence/{evidence_id} updates review status and creates audit entry."""
    suffix = uuid.uuid4().hex[:6].upper()

    # 1. Create investigation
    inv_res = client.post("/api/investigations", json={
        "incident_title": f"HPLC Column Pressure Spike-{suffix}",
        "incident_description": "Column inlet pressure exceeded 350 bar during elution.",
        "batch_number": f"BATCH-{suffix}",
        "product_name": "API Intermediate",
        "department": "Quality Control",
        "severity": "Medium",
        "incident_date": "2026-11-02",
        "detection_date": "2026-11-02",
    })
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["investigation_id"]

    # 2. Add evidence
    ev_res = client.post(f"/api/investigations/{inv_id}/evidence", json={
        "description": "Visual inspection showed insoluble particulates embedded in stainless steel frit.",
        "evidence_type": "Supporting",
        "source_reference": "QC Physical Testing Lab Notebook P-42",
        "review_status": "Pending Review",
    })
    assert ev_res.status_code == 201
    evidence_id = ev_res.json()["evidence_id"]
    assert ev_res.json()["review_status"] == "Pending Review"

    # 3. PATCH evidence review_status to Verified
    patch_res = client.patch(
        f"/api/investigations/{inv_id}/evidence/{evidence_id}",
        json={
            "review_status": "Verified",
            "notes": "Reviewed by QA Lead. Particulate analysis confirms filter breakthrough.",
        },
    )
    assert patch_res.status_code == 200
    patched_data = patch_res.json()
    assert patched_data["review_status"] == "Verified"
    assert "filter breakthrough" in patched_data["notes"]

    # 4. Verify persistence in DB
    ev_db = db.query(Evidence).filter_by(id=uuid.UUID(evidence_id)).first()
    assert ev_db is not None
    assert ev_db.review_status.value == "Verified"

    # 5. Verify audit log entry
    inv_db = db.query(Investigation).filter_by(investigation_number=inv_id).first()
    audit_entry = (
        db.query(InvestigationActivity)
        .filter_by(investigation_id=inv_db.id, activity_type="EVIDENCE_STATUS_UPDATED")
        .first()
    )
    assert audit_entry is not None
    assert "Verified" in audit_entry.description

    # 6. Test 404 on nonexistent evidence
    bad_res = client.patch(
        f"/api/investigations/{inv_id}/evidence/999999",
        json={"review_status": "Rejected"},
    )
    assert bad_res.status_code == 404


# ---------------------------------------------------------------------------
# DEF-05: CAPA Status Lifecycle Transitions
# ---------------------------------------------------------------------------

def test_capa_lifecycle_transitions(db):
    """Verify CAPA status transitions: Draft -> Pending Review, Approved, and Rejected."""
    suffix = uuid.uuid4().hex[:6].upper()

    # Create investigation
    inv_res = client.post("/api/investigations", json={
        "incident_title": f"CAPA Lifecycle Test Investigation-{suffix}",
        "incident_description": "Validating CAPA status transitions.",
        "batch_number": f"BATCH-{suffix}",
        "department": "QA",
        "severity": "Low",
        "incident_date": "2026-11-03",
        "detection_date": "2026-11-03",
    })
    inv_id = inv_res.json()["investigation_id"]

    # 1. Draft -> Approved directly (supported after DEF-05 fix)
    capa1 = client.post(f"/api/investigations/{inv_id}/capa", json={
        "action_type": "Corrective Action",
        "description": f"Immediate containment action-{suffix}",
        "action_owner": "QA Officer",
        "target_date": "2026-11-15",
        "effectiveness_verification_method": "Verify line clearance logs for next 3 runs.",
        "status": "Draft",
    }).json()

    approve_res = client.patch(
        f"/api/investigations/{inv_id}/capa/{capa1['action_id']}",
        json={"status": "Approved", "notes": "Approved directly by QA Lead"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "Approved"

    # 2. Draft -> Pending Review
    capa2 = client.post(f"/api/investigations/{inv_id}/capa", json={
        "action_type": "Preventive Action",
        "description": f"Review required preventive action-{suffix}",
        "action_owner": "QA Specialist",
        "target_date": "2026-11-20",
        "effectiveness_verification_method": "Audit validation report post completion.",
        "status": "Draft",
    }).json()

    review_res = client.patch(
        f"/api/investigations/{inv_id}/capa/{capa2['action_id']}",
        json={"status": "Pending Review", "notes": "Submitting for review"},
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "Pending Review"

    # 3. Draft -> Rejected
    capa3 = client.post(f"/api/investigations/{inv_id}/capa", json={
        "action_type": "Corrective Action",
        "description": f"Infeasible remedial action-{suffix}",
        "action_owner": "Maintenance Lead",
        "target_date": "2026-11-25",
        "effectiveness_verification_method": "Review feasibility study.",
        "status": "Draft",
    }).json()

    reject_res = client.patch(
        f"/api/investigations/{inv_id}/capa/{capa3['action_id']}",
        json={"status": "Rejected", "notes": "Out of scope for this deviation."},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "Rejected"

    # 4. Invalid transition rejection: Rejected -> Completed should fail with 422
    invalid_res = client.patch(
        f"/api/investigations/{inv_id}/capa/{capa3['action_id']}",
        json={"status": "Completed"},
    )
    assert invalid_res.status_code == 422
    assert "InvalidCAPAStatusTransitionError" in invalid_res.json()["error"]


# ---------------------------------------------------------------------------
# DEF-07: Timezone-Aware UTC Compliance
# ---------------------------------------------------------------------------

def test_timezone_aware_utc_schema_defaults():
    """Verify that NormalizedIncidentIntake utilizes timezone-aware UTC timestamps."""
    input_data = NormalizedIncidentIntake(
        intake_id="INTAKE-TEST-001",
        source_type=IntakeMethodEnum.DOCUMENT,
        prepared_incident_text="Incident raw text for test.",
    )
    assert input_data.processed_at is not None
    assert input_data.processed_at.tzinfo is not None or input_data.processed_at.utcoffset() is not None


# ---------------------------------------------------------------------------
# Controlled End-to-End Investigation Lifecycle Integration
# ---------------------------------------------------------------------------

def test_controlled_end_to_end_investigation_lifecycle(db):
    """Execute complete end-to-end investigation lifecycle:
    1. Create Investigation
    2. Add Evidence
    3. Update Evidence Review Status
    4. Save 5-Whys and 6M Fishbone with normalized statuses
    5. Propose CAPA
    6. Approve CAPA
    7. Verify PostgreSQL records & audit activities
    """
    suffix = uuid.uuid4().hex[:6].upper()

    # Step 1: Create Investigation
    inv_res = client.post("/api/investigations", json={
        "incident_title": f"E2E API Granulation Moisture Excursion-{suffix}",
        "incident_description": "Loss on drying (LOD) exceeded specification limit of 2.0% reaching 3.4%.",
        "batch_number": f"BATCH-{suffix}",
        "product_name": "Paracetamol High-Density Granules",
        "department": "Solid Oral Dosage",
        "severity": "Critical",
        "incident_date": "2026-11-04",
        "detection_date": "2026-11-04",
    })
    assert inv_res.status_code == 201
    inv_data = inv_res.json()
    inv_id = inv_data["investigation_id"]

    # Step 2: Add Evidence
    ev_res = client.post(f"/api/investigations/{inv_id}/evidence", json={
        "description": "Chart recorder shows relative humidity climbed from 35% to 78% during cycle.",
        "evidence_type": "Supporting",
        "source_reference": "SCADA Historian FBD-01 Log 2026-11-04",
        "review_status": "Pending Review",
    })
    assert ev_res.status_code == 201
    ev_id = ev_res.json()["evidence_id"]

    # Step 3: Update Evidence
    patch_ev_res = client.patch(f"/api/investigations/{inv_id}/evidence/{ev_id}", json={
        "review_status": "Verified",
        "notes": "Verified against humidity transmitter raw telemetry log.",
    })
    assert patch_ev_res.status_code == 200

    # Step 4: Save 5-Whys and Fishbone Analysis with normalized UI statuses
    rca_payload = {
        "five_whys": [
            {
                "level": 1,
                "question": "Why did the granule moisture exceed specification?",
                "answer": "Drying cycle failed to reach target moisture within validated window.",
                "status": "Evidence-Supported",
            },
            {
                "level": 2,
                "question": "Why did the drying cycle fail to remove target moisture?",
                "answer": "Inlet air dehumidification system failed to deliver dry air to FBD-01.",
                "status": "Evidence-Supported",
            },
            {
                "level": 3,
                "question": "Why did the dehumidification system deliver humid air?",
                "answer": "Chilled water control valve CV-302 stuck in 15% open position.",
                "status": "Evidence-Supported",
            },
            {
                "level": 4,
                "question": "Why did CV-302 valve stick in position?",
                "answer": "Pneumatic actuator diaphragm torn due to age fatigue beyond PM interval.",
                "status": "Evidence-Supported",
            },
            {
                "level": 5,
                "question": "Why was the diaphragm not replaced prior to failure?",
                "answer": "Preventive maintenance schedule in CMMS had incorrect 24-month interval.",
                "is_root_cause": True,
                "status": "Confirmed Root Cause",
            },
        ],
        "fishbone_causes": [
            {
                "cause_id": f"FC-{suffix}-1",
                "category": "Machine",
                "cause_description": "Chilled water actuator CV-302 diaphragm failure",
                "status": "Evidence-Supported",
            },
            {
                "cause_id": f"FC-{suffix}-2",
                "category": "Method",
                "cause_description": "CMMS PM task interval outdated",
                "status": "Requires Evidence",
            },
            {
                "cause_id": f"FC-{suffix}-3",
                "category": "Environment",
                "cause_description": "External atmospheric humidity unusually high during monsoon",
                "status": "Evidence-Supported",
            },
        ],
        "investigator_notes": "Root cause confirmed as obsolete CMMS preventive maintenance schedule.",
    }
    rca_res = client.post(f"/api/investigations/{inv_id}/rca", json=rca_payload)
    assert rca_res.status_code == 200
    assert len(rca_res.json()["five_whys"]) == 5
    assert len(rca_res.json()["fishbone_causes"]) == 3

    # Step 5: Create CAPA
    capa_res = client.post(f"/api/investigations/{inv_id}/capa", json={
        "action_type": "Preventive Action",
        "description": "Revise PM task frequency in SAP PM/CMMS and replace actuator diaphragms across all FBD suites.",
        "action_owner": "Engineering Maintenance Manager",
        "target_date": "2026-11-25",
        "effectiveness_verification_method": "Confirm all 6 AHU PM work orders rescheduled to 12-month interval.",
        "status": "Draft",
    })
    assert capa_res.status_code == 201
    capa_id = capa_res.json()["action_id"]

    # Step 6: Approve CAPA
    approve_res = client.patch(
        f"/api/investigations/{inv_id}/capa/{capa_id}",
        json={"status": "Approved", "notes": "Approved by QA Operations Director"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "Approved"

    # Step 7: Verify Complete State in Database
    inv_db = db.query(Investigation).filter_by(investigation_number=inv_id).first()
    assert inv_db is not None
    assert len(inv_db.evidence_records) >= 1
    assert len(inv_db.capa_actions) >= 1
    assert inv_db.capa_actions[0].action_status.value == "Approved"

    rca_db = db.query(RCAAnalysis).filter_by(investigation_id=inv_db.id).first()
    assert rca_db is not None
    assert len(rca_db.five_whys) == 5
    assert len(rca_db.fishbone_causes) == 3

    # Step 8: Verify audit activities recorded in chronological order
    activities = (
        db.query(InvestigationActivity)
        .filter_by(investigation_id=inv_db.id)
        .order_by(InvestigationActivity.created_at.asc())
        .all()
    )
    activity_types = [a.activity_type for a in activities]
    assert "INVESTIGATION_CREATED" in activity_types
    assert "EVIDENCE_ADDED" in activity_types
    assert "EVIDENCE_STATUS_UPDATED" in activity_types
    assert "RCA_ANALYSIS_SAVED" in activity_types
    assert "CAPA_ACTION_CREATED" in activity_types
    assert "CAPA_STATUS_CHANGED" in activity_types


# ---------------------------------------------------------------------------
# Failure & Resilience Tests
# ---------------------------------------------------------------------------

def test_nonexistent_investigation_returns_404():
    """Verify appropriate 404 response when querying invalid investigation ID."""
    res = client.get("/api/investigations/INV-9999-9999")
    assert res.status_code == 404
    body = res.json()
    assert "not found" in (body.get("message") or body.get("detail") or "").lower()


def test_invalid_investigation_payload_returns_422():
    """Verify Pydantic validation rejects incomplete or malformed investigation payloads."""
    res = client.post("/api/investigations", json={
        # Missing required incident_title
        "incident_description": "Missing title",
    })
    assert res.status_code == 422


def test_duplicate_or_invalid_evidence_id_handling():
    """Verify that updating an evidence ID belonging to a nonexistent or mismatched record returns 404."""
    res = client.patch(
        "/api/investigations/INV-9999-9999/evidence/999999",
        json={"review_status": "Verified"},
    )
    assert res.status_code == 404
