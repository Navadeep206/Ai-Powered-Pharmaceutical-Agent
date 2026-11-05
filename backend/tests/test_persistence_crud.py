"""Comprehensive integration and persistence tests for Step 04 Phase 3 CRUD operations."""

import io
import uuid
import pytest
from fastapi.testclient import TestClient
from app.database.session import SessionLocal
from app.main import app
from app.models.activity import InvestigationActivity
from app.models.capa import CapaAction
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.rca import RCAAnalysis
from tests.conftest import build_pdf_with_text

client = TestClient(app)


@pytest.fixture
def db():
    """Provides a fresh database session for direct inspection."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_investigation_full_persistence_lifecycle(db):
    """Test full CRUD lifecycle for investigations: create, get, list, filter, search, and patch."""
    suffix = uuid.uuid4().hex[:6].upper()
    title = f"Vacuum loss in distillation column DC-{suffix}"

    create_payload = {
        "incident_title": title,
        "incident_description": "Column operating vacuum collapsed from 15 mbar to atmospheric pressure.",
        "deviation_id": f"DEV-{suffix}",
        "batch_number": f"BATCH-{suffix}",
        "product_name": "API Intermediate X",
        "department": "Distillation",
        "severity": "High",
        "incident_date": "2026-11-01",
        "detection_date": "2026-11-01",
    }

    # 1. POST /api/investigations
    create_res = client.post("/api/investigations", json=create_payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    inv_num = created_data["investigation_id"]
    assert inv_num.startswith("INV-")
    assert created_data["investigation_status"] == "Open"

    # Verify directly in PostgreSQL
    inv_db = db.query(Investigation).filter_by(investigation_number=inv_num).first()
    assert inv_db is not None
    assert inv_db.incident_title == title
    assert inv_db.department == "Distillation"

    # 2. GET /api/investigations/{id} by tracking number and by UUID
    get_by_num_res = client.get(f"/api/investigations/{inv_num}")
    assert get_by_num_res.status_code == 200
    assert get_by_num_res.json()["incident_title"] == title

    get_by_uuid_res = client.get(f"/api/investigations/{inv_db.id}")
    assert get_by_uuid_res.status_code == 200
    assert get_by_uuid_res.json()["investigation_id"] == inv_num

    # 3. GET /api/investigations with search, department, and severity filters
    list_res = client.get(f"/api/investigations?search={suffix}&department=Distillation&severity=High")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["pagination"]["total"] >= 1
    found_nums = [item["investigation_id"] for item in list_data["items"]]
    assert inv_num in found_nums

    # 4. PATCH /api/investigations/{id}
    patch_payload = {
        "investigation_status": "Under Investigation",
        "observed_impact": "Loss of batch yield, vacuum seal gasket replaced.",
    }
    patch_res = client.patch(f"/api/investigations/{inv_num}", json=patch_payload)
    assert patch_res.status_code == 200
    assert patch_res.json()["investigation_status"] == "Under Investigation"
    assert patch_res.json()["observed_impact"] == patch_payload["observed_impact"]

    # 5. Verify 404 for nonexistent investigation
    missing_res = client.get("/api/investigations/INV-DOES-NOT-EXIST")
    assert missing_res.status_code == 404


def test_document_metadata_persistence(db):
    """Test that uploading a PDF with an investigation ID persists document metadata in PostgreSQL."""
    # 1. Create an investigation
    inv_payload = {
        "incident_title": "Centrifuge C-301 basket balance excursion",
        "incident_description": "Vibration sensor detected severe imbalance during cake wash step.",
        "severity": "Medium",
        "department": "Centrifugation",
    }
    inv_res = client.post("/api/investigations", json=inv_payload)
    inv_id = inv_res.json()["investigation_id"]

    # 2. Upload PDF linked to the investigation
    pdf_bytes = build_pdf_with_text(["Batch Record 884: Centrifuge basket vibration spike observed."])
    upload_res = client.post(
        f"/api/documents/upload?investigation_id={inv_id}",
        files={"file": ("centrifuge_incident_report.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 201
    assert upload_res.json()["extraction_status"] == "Success"

    # 3. Query documents endpoint for this investigation
    docs_res = client.get(f"/api/investigations/{inv_id}/documents")
    assert docs_res.status_code == 200
    docs = docs_res.json()
    assert len(docs) >= 1
    assert docs[0]["original_filename"] == "centrifuge_incident_report.pdf"
    assert docs[0]["extraction_status"] == "Success"

    # Verify directly in PostgreSQL
    inv_db = db.query(Investigation).filter_by(investigation_number=inv_id).first()
    db_docs = db.query(Document).filter_by(investigation_id=inv_db.id).all()
    assert len(db_docs) >= 1
    assert db_docs[0].original_filename == "centrifuge_incident_report.pdf"
    # Verify no raw binary blob stored in PostgreSQL
    assert not hasattr(db_docs[0], "file_binary")


def test_rca_persistence_and_transaction_safety(db):
    """Test saving and retrieving 5-Whys and Fishbone causes, and verify transaction rollback on error."""
    inv_payload = {
        "incident_title": "OOS Total Impurities in Batch 5510",
        "incident_description": "HPLC assay detected 0.62% unknown impurity exceeding the 0.20% specification limit.",
        "severity": "Critical",
        "department": "Synthesis",
    }
    inv_res = client.post("/api/investigations", json=inv_payload)
    inv_id = inv_res.json()["investigation_id"]

    rca_payload = {
        "five_whys": [
            {
                "level": 1,
                "question": "Why did total impurities exceed 0.20%?",
                "answer": "Side-reaction occurred during acetylation step.",
            },
            {
                "level": 2,
                "question": "Why did side-reaction occur?",
                "answer": "Reaction temperature was 8C higher than setpoint.",
            },
            {
                "level": 3,
                "question": "Why was reaction temperature 8C higher?",
                "answer": "Cooling water valve stuck in 25% open position.",
                "is_root_cause": True,
            },
        ],
        "fishbone_causes": [
            {
                "cause_id": "CAUSE-01",
                "category": "Machine",
                "cause_description": "Cooling control valve actuator diaphragm perished.",
                "evidence_references": ["EVD-VALVE-01"],
                "status": "AI Suggestion",
            },
            {
                "cause_id": "CAUSE-02",
                "category": "Method",
                "cause_description": "Preventive maintenance interval for valve actuator exceeded by 3 months.",
                "evidence_references": ["EVD-PM-02"],
                "status": "AI Suggestion",
            },
        ],
        "investigator_notes": "Acetylation exotherm unchecked due to cooling valve mechanical failure.",
    }

    # 1. Save RCA
    post_res = client.post(f"/api/investigations/{inv_id}/rca", json=rca_payload)
    assert post_res.status_code == 200
    rca_data = post_res.json()
    assert len(rca_data["five_whys"]) == 3
    assert rca_data["five_whys"][2]["is_root_cause"] is True
    assert len(rca_data["fishbone_causes"]) == 2

    # 2. Get RCA
    get_res = client.get(f"/api/investigations/{inv_id}/rca")
    assert get_res.status_code == 200
    assert len(get_res.json()["five_whys"]) == 3

    # 3. Test validation error and transaction rollback: Non-sequential why level (level 5 without level 4)
    invalid_rca_payload = {
        "five_whys": [
            {
                "level": 1,
                "question": "Why 1?",
                "answer": "Answer 1",
            },
            {
                "level": 5,  # Invalid jump from 1 to 5
                "question": "Why 5?",
                "answer": "Answer 5",
            },
        ],
        "fishbone_causes": [],
    }
    err_res = client.post(f"/api/investigations/{inv_id}/rca", json=invalid_rca_payload)
    assert err_res.status_code == 422

    # Verify that the original RCA data was NOT corrupted by the failed payload
    recheck_res = client.get(f"/api/investigations/{inv_id}/rca")
    assert len(recheck_res.json()["five_whys"]) == 3


def test_evidence_persistence_and_categorization(db):
    """Test persisting supporting, contradictory, and missing evidence items."""
    inv_payload = {
        "incident_title": "Sterile filtration integrity test failure",
        "incident_description": "Bubble point test failed at 2.4 bar (specification >= 3.2 bar).",
        "severity": "Critical",
        "department": "Sterile Manufacturing",
    }
    inv_res = client.post("/api/investigations", json=inv_payload)
    inv_id = inv_res.json()["investigation_id"]

    # 1. Add supporting evidence
    sup_res = client.post(
        f"/api/investigations/{inv_id}/evidence",
        json={
            "description": "Integrity tester calibration certificate verified valid on test date.",
            "evidence_type": "Supporting",
            "source_reference": "CAL-INTEG-2026-08",
            "review_status": "Verified",
        },
    )
    assert sup_res.status_code == 201
    assert sup_res.json()["evidence_type"] == "Supporting"

    # 2. Add contradictory evidence
    con_res = client.post(
        f"/api/investigations/{inv_id}/evidence",
        json={
            "description": "Pre-use integrity test passed at 3.3 bar using the same test instrument.",
            "evidence_type": "Contradictory",
            "source_reference": "BATCH-LOG-P12",
            "review_status": "Pending Review",
        },
    )
    assert con_res.status_code == 201
    assert con_res.json()["evidence_type"] == "Contradictory"

    # 3. Add missing evidence gap
    gap_res = client.post(
        f"/api/investigations/{inv_id}/evidence",
        json={
            "description": "Missing wet-out flushing volume verification log for filter housing H-2.",
            "evidence_type": "Missing Evidence",
            "source_reference": "GAP-ANALYSIS-01",
            "review_status": "Pending Review",
        },
    )
    assert gap_res.status_code == 201
    assert gap_res.json()["evidence_type"] == "Missing Evidence"

    # 4. List all evidence
    list_res = client.get(f"/api/investigations/{inv_id}/evidence")
    assert list_res.status_code == 200
    evidence_items = list_res.json()
    assert len(evidence_items) == 3
    types = {item["evidence_type"] for item in evidence_items}
    assert types == {"Supporting", "Contradictory", "Missing Evidence"}


def test_capa_persistence_and_status_transitions(db):
    """Test CAPA creation, listing, and lifecycle state transitions."""
    inv_payload = {
        "incident_title": "Label printer barcode unreadable in Packaging Line 2",
        "incident_description": "Thermal transfer print ribbon misaligned causing barcode scan rate drop to 68%.",
        "severity": "Medium",
        "department": "Packaging",
    }
    inv_res = client.post("/api/investigations", json=inv_payload)
    inv_id = inv_res.json()["investigation_id"]

    # 1. Create Corrective Action
    create_payload = {
        "action_type": "Corrective Action",
        "description": "Realign thermal transfer printhead and install inline 2D barcode scanner.",
        "action_owner": "Packaging Maintenance Engineer",
        "target_date": "2026-11-20",
        "effectiveness_verification_method": "Verify 100% 2D barcode scan verification over 5 consecutive batch runs.",
        "status": "Draft",
    }
    capa_res = client.post(f"/api/investigations/{inv_id}/capa", json=create_payload)
    assert capa_res.status_code == 201
    capa_data = capa_res.json()
    capa_id = capa_data["action_id"]
    assert capa_data["status"] == "Draft"

    # 2. Transition Draft -> Proposed
    prop_res = client.patch(
        f"/api/investigations/{inv_id}/capa/{capa_id}",
        json={"status": "Proposed", "notes": "Submitted for QA review."},
    )
    assert prop_res.status_code == 200
    assert prop_res.json()["status"] == "Proposed"

    # 3. Transition Proposed -> Approved
    app_res = client.patch(
        f"/api/investigations/{inv_id}/capa/{capa_id}",
        json={"status": "Approved", "notes": "Approved by QA Director."},
    )
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "Approved"

    # 4. Transition Approved -> In Progress
    prog_res = client.patch(
        f"/api/investigations/{inv_id}/capa/{capa_id}",
        json={"status": "In Progress"},
    )
    assert prog_res.status_code == 200
    assert prog_res.json()["status"] == "In Progress"

    # 5. Invalid transition: In Progress directly to Closed (must be Completed first)
    invalid_res = client.patch(
        f"/api/investigations/{inv_id}/capa/{capa_id}",
        json={"status": "Closed"},
    )
    assert invalid_res.status_code == 422


def test_dashboard_summary_metrics(db):
    """Test that /api/dashboard/summary calculates genuine counts from PostgreSQL."""
    # Get initial dashboard state
    init_res = client.get("/api/dashboard/summary")
    assert init_res.status_code == 200
    init_data = init_res.json()
    initial_total = init_data["total_investigations"]
    initial_open = init_data["open_investigations"]

    # Create a new investigation in Open status
    new_inv = {
        "incident_title": "Dashboard Metric Verification Deviation",
        "incident_description": "Testing dynamic PostgreSQL count aggregation.",
        "severity": "Low",
        "department": "Quality Assurance",
    }
    client.post("/api/investigations", json=new_inv)

    # Re-check summary: total and open must increment by 1
    updated_res = client.get("/api/dashboard/summary")
    assert updated_res.status_code == 200
    updated_data = updated_res.json()
    assert updated_data["total_investigations"] == initial_total + 1
    assert updated_data["open_investigations"] == initial_open + 1


def test_investigation_activity_logging(db):
    """Verify that domain operations record audit trail activities in PostgreSQL."""
    inv_payload = {
        "incident_title": "Activity Audit Trail Verification",
        "incident_description": "Ensuring all state modifications record activity history entries.",
        "severity": "Medium",
        "department": "Operations",
    }
    inv_res = client.post("/api/investigations", json=inv_payload)
    inv_id = inv_res.json()["investigation_id"]

    inv_db = db.query(Investigation).filter_by(investigation_number=inv_id).first()
    assert inv_db is not None

    activities = db.query(InvestigationActivity).filter_by(investigation_id=inv_db.id).all()
    assert len(activities) >= 1
    activity_types = [a.activity_type for a in activities]
    assert "INVESTIGATION_CREATED" in activity_types


def test_data_survives_new_database_session():
    """Verify that persisted data survives session closure and can be retrieved from fresh session."""
    unique_suffix = uuid.uuid4().hex[:8].upper()
    inv_num = f"INV-SESSION-{unique_suffix}"

    # Session 1: Create and commit
    with SessionLocal() as session1:
        inv = Investigation(
            investigation_number=inv_num,
            incident_title="Session Persistence Test",
            incident_description="Verifying that committed records persist across independent sessions.",
        )
        session1.add(inv)
        session1.commit()

    # Session 2: Read from a brand-new connection/session
    with SessionLocal() as session2:
        queried = session2.query(Investigation).filter_by(investigation_number=inv_num).first()
        assert queried is not None
        assert queried.incident_title == "Session Persistence Test"
