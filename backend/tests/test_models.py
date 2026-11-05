"""Unit and integration tests for SQLAlchemy 2.0 ORM models and relationships."""

import uuid
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from app.database.session import Base, SessionLocal
from app.models import (
    CapaAction,
    Document,
    Evidence,
    FishboneCause,
    FiveWhy,
    Investigation,
    InvestigationActivity,
    RCAAnalysis,
)
from app.schemas.capa import CAPAStatusEnum, CAPATypeEnum
from app.schemas.document import IntakeMethodEnum
from app.schemas.evidence import EvidenceReviewStatusEnum, EvidenceTypeEnum
from app.schemas.investigation import InvestigationStatusEnum, SeverityEnum
from app.schemas.rca import CauseVerificationStatusEnum, FishboneCategoryEnum


@pytest.fixture
def db_session():
    """Provides a transactional database session rolled back after each test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_all_models_registered_in_metadata():
    """Verify that all 8 domain models are registered in SQLAlchemy DeclarativeBase metadata."""
    registered_tables = set(Base.metadata.tables.keys())
    expected_tables = {
        "investigations",
        "documents",
        "rca_analyses",
        "five_whys",
        "fishbone_causes",
        "evidence_records",
        "capa_actions",
        "investigation_activities",
    }
    assert expected_tables.issubset(registered_tables), f"Missing tables: {expected_tables - registered_tables}"


def test_investigation_model_schema_attributes():
    """Verify column definitions and properties on the Investigation model."""
    mapper = inspect(Investigation)
    columns = {col.key: col for col in mapper.columns}

    assert "id" in columns
    assert columns["id"].primary_key is True
    assert "investigation_number" in columns
    assert columns["investigation_number"].unique is True
    assert "severity" in columns
    assert "investigation_status" in columns
    assert "department" in columns
    assert "created_at" in columns
    assert "closed_at" in columns

    # Verify relationships defined
    relationships = {rel.key for rel in mapper.relationships}
    assert {"documents", "rca_analyses", "evidence_records", "capa_actions", "activities"}.issubset(relationships)


def test_activity_metadata_column_mapping():
    """Verify that activity_metadata maps to the underlying 'metadata' column without naming clash."""
    mapper = inspect(InvestigationActivity)
    # The Python property should be 'activity_metadata'
    assert "activity_metadata" in mapper.columns
    # The underlying database column name must be 'metadata'
    col = mapper.columns["activity_metadata"]
    assert col.name == "metadata"


def test_five_whys_table_constraints():
    """Verify CheckConstraint and UniqueConstraint configuration on five_whys table."""
    table = FiveWhy.__table__
    constraint_names = {c.name for c in table.constraints}
    assert "ck_five_whys_range" in constraint_names
    assert "uq_rca_analysis_why_number" in constraint_names


def test_full_investigation_lifecycle_persistence(db_session):
    """Integration test: Create an investigation with child entities and verify bidirectional navigation."""
    unique_suffix = uuid.uuid4().hex[:8].upper()
    inv_num = f"INV-2026-{unique_suffix}"

    # 1. Create Investigation
    investigation = Investigation(
        investigation_number=inv_num,
        incident_title="Out-of-Specification pH during API precipitation",
        incident_description="Batch 8841 failed pH specification (measured 4.12 vs required 5.5-6.5).",
        deviation_id=f"DEV-{unique_suffix}",
        batch_number=f"B-{unique_suffix}",
        product_name="Atorvastatin Calcium API",
        department="Manufacturing",
        severity=SeverityEnum.HIGH,
        investigation_status=InvestigationStatusEnum.OPEN,
    )
    db_session.add(investigation)
    db_session.flush()

    # 2. Attach Document
    doc = Document(
        investigation_id=investigation.id,
        original_filename="batch_8841_manufacturing_record.pdf",
        content_type="application/pdf",
        file_size=204850,
        page_count=3,
        source_type=IntakeMethodEnum.DOCUMENT,
        extraction_status="Success",
        extracted_text="Precipitation tank pH meter reading: 4.12 at 14:22 UTC.",
        page_metadata=[{"page_number": 1, "character_count": 52}],
    )
    db_session.add(doc)

    # 3. Attach Evidence
    evidence = Evidence(
        investigation_id=investigation.id,
        evidence_type=EvidenceTypeEnum.SUPPORTING,
        description="Calibration buffer solution pH 7.0 expired 14 days prior to batch processing.",
        source_reference="Calibration Log CAL-2026-092",
        review_status=EvidenceReviewStatusEnum.VERIFIED,
        notes="Buffer bottle lot BF-441 expired on Jan 15.",
    )
    db_session.add(evidence)

    # 4. Attach Activity
    activity = InvestigationActivity(
        investigation_id=investigation.id,
        activity_type="INTAKE_LOGGED",
        description="Initial deviation record created from automated SCADA alert.",
        actor_identifier="qa_specialist_smith",
        activity_metadata={"source": "SCADA_ALERT_33", "trigger_value": 4.12},
    )
    db_session.add(activity)

    # 5. Attach RCA Analysis with 5-Whys and Fishbone Causes
    rca = RCAAnalysis(
        investigation_id=investigation.id,
        analysis_method="COMBINED",
        analysis_status="Under Review",
        summary="Expired buffer solution caused pH electrode calibration drift.",
    )
    db_session.add(rca)
    db_session.flush()

    why1 = FiveWhy(
        rca_analysis_id=rca.id,
        why_number=1,
        question="Why was the precipitate pH 4.12 instead of 5.5-6.5?",
        answer="Excess hydrochloric acid was added during neutralizing titration.",
        is_root_cause=False,
    )
    why2 = FiveWhy(
        rca_analysis_id=rca.id,
        why_number=2,
        question="Why was excess acid added?",
        answer="The online pH sensor misreported the slurry pH as 6.2 when it was actually 4.8.",
        is_root_cause=False,
    )
    why3 = FiveWhy(
        rca_analysis_id=rca.id,
        why_number=3,
        question="Why did the pH sensor report incorrect values?",
        answer="The sensor had been calibrated with expired reference buffer solution.",
        is_root_cause=True,
    )
    db_session.add_all([why1, why2, why3])

    fishbone = FishboneCause(
        rca_analysis_id=rca.id,
        category=FishboneCategoryEnum.MATERIAL,
        cause_description="Expired pH buffer solution in instrumentation prep room.",
        cause_origin="Investigator Added",
        review_status=CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE,
        reviewed_by="Lead QA Investigator",
        reviewed_at=datetime.now(timezone.utc),
    )
    db_session.add(fishbone)
    db_session.flush()

    # 6. Attach CAPA Action
    capa = CapaAction(
        investigation_id=investigation.id,
        related_root_cause_id=fishbone.id,
        action_type=CAPATypeEnum.CORRECTIVE_ACTION,
        description="Quarantine expired buffer lots and implement barcode verification in calibration SOP.",
        action_owner="Instrumentation Dept Head",
        target_date=date(2026, 12, 1),
        effectiveness_verification="Verify zero expired reagents present across 3 monthly audit cycles.",
        action_status=CAPAStatusEnum.PROPOSED,
    )
    db_session.add(capa)
    db_session.commit()

    # 7. Query and Verify Bidirectional Navigation
    queried_inv = db_session.query(Investigation).filter_by(investigation_number=inv_num).first()
    assert queried_inv is not None
    assert len(queried_inv.documents) == 1
    assert queried_inv.documents[0].original_filename == "batch_8841_manufacturing_record.pdf"
    assert queried_inv.documents[0].investigation.id == queried_inv.id

    assert len(queried_inv.evidence_records) == 1
    assert queried_inv.evidence_records[0].evidence_type == EvidenceTypeEnum.SUPPORTING

    assert len(queried_inv.activities) == 1
    assert queried_inv.activities[0].activity_metadata["trigger_value"] == 4.12
    assert queried_inv.activities[0].activity_type == "INTAKE_LOGGED"

    assert len(queried_inv.rca_analyses) == 1
    queried_rca = queried_inv.rca_analyses[0]
    assert len(queried_rca.five_whys) == 3
    assert queried_rca.five_whys[2].is_root_cause is True
    assert len(queried_rca.fishbone_causes) == 1
    assert queried_rca.fishbone_causes[0].category == FishboneCategoryEnum.MATERIAL

    assert len(queried_inv.capa_actions) == 1
    queried_capa = queried_inv.capa_actions[0]
    assert queried_capa.action_type == CAPATypeEnum.CORRECTIVE_ACTION
    assert queried_capa.related_root_cause.id == fishbone.id
    assert queried_capa.related_root_cause.cause_description == fishbone.cause_description


def test_five_whys_unique_constraint(db_session):
    """Verify that duplicate why_number for the same RCA analysis raises IntegrityError."""
    unique_suffix = uuid.uuid4().hex[:8].upper()
    investigation = Investigation(
        investigation_number=f"INV-UQ-{unique_suffix}",
        incident_title="Duplicate Why Test",
        incident_description="Testing unique constraint on why numbers.",
    )
    db_session.add(investigation)
    db_session.flush()

    rca = RCAAnalysis(investigation_id=investigation.id)
    db_session.add(rca)
    db_session.flush()

    why_a = FiveWhy(rca_analysis_id=rca.id, why_number=1, question="Why 1?", answer="Answer 1")
    why_b = FiveWhy(rca_analysis_id=rca.id, why_number=1, question="Duplicate Why 1?", answer="Answer duplicate")
    db_session.add(why_a)
    db_session.add(why_b)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_five_whys_check_constraint_range(db_session):
    """Verify that why_number out of 1..5 range raises IntegrityError."""
    unique_suffix = uuid.uuid4().hex[:8].upper()
    investigation = Investigation(
        investigation_number=f"INV-CK-{unique_suffix}",
        incident_title="Check Constraint Test",
        incident_description="Testing range constraint on why numbers.",
    )
    db_session.add(investigation)
    db_session.flush()

    rca = RCAAnalysis(investigation_id=investigation.id)
    db_session.add(rca)
    db_session.flush()

    # why_number=6 should violate ck_five_whys_range
    invalid_why = FiveWhy(rca_analysis_id=rca.id, why_number=6, question="Why 6?", answer="Out of bounds")
    db_session.add(invalid_why)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_rca_cascade_deletion(db_session):
    """Verify that deleting an RCA analysis cascades and deletes child FiveWhys and FishboneCauses."""
    unique_suffix = uuid.uuid4().hex[:8].upper()
    investigation = Investigation(
        investigation_number=f"INV-CAS-{unique_suffix}",
        incident_title="Cascade Test",
        incident_description="Testing cascade deletion from RCA to child whys and fishbone.",
    )
    db_session.add(investigation)
    db_session.flush()

    rca = RCAAnalysis(investigation_id=investigation.id)
    db_session.add(rca)
    db_session.flush()

    why = FiveWhy(rca_analysis_id=rca.id, why_number=1, question="Why?", answer="Because")
    cause = FishboneCause(
        rca_analysis_id=rca.id,
        category=FishboneCategoryEnum.MACHINE,
        cause_description="Valve seal failure",
    )
    db_session.add_all([why, cause])
    db_session.commit()

    rca_id = rca.id
    why_id = why.id
    cause_id = cause.id

    # Delete the RCA analysis
    db_session.delete(rca)
    db_session.commit()

    # Verify children are deleted
    assert db_session.get(RCAAnalysis, rca_id) is None
    assert db_session.get(FiveWhy, why_id) is None
    assert db_session.get(FishboneCause, cause_id) is None


def test_investigation_number_uniqueness(db_session):
    """Verify unique constraint on investigation_number."""
    unique_suffix = uuid.uuid4().hex[:8].upper()
    inv_num = f"INV-DUP-{unique_suffix}"

    inv1 = Investigation(
        investigation_number=inv_num,
        incident_title="First Investigation",
        incident_description="First description",
    )
    inv2 = Investigation(
        investigation_number=inv_num,
        incident_title="Second Investigation (Duplicate Number)",
        incident_description="Second description",
    )
    db_session.add(inv1)
    db_session.commit()

    db_session.add(inv2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
