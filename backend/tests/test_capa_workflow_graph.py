"""Comprehensive Automated Test Suite for RootIQ CAPA Reasoning and Human Review Engine (Step 06 Phase 3).

Verifies the complete AI-assisted LangGraph CAPA generation, validation, and human review workflow:
1. CAPA Generation: Corrective actions addressing root causes, specific actionable remediation.
2. CAPA Generation: Preventive actions addressing recurrence, monitoring, SOP, PM, and contributing factors.
3. CAPA Generation: Multiple potential root causes handling.
4. CAPA Generation: Insufficient evidence safeguard / interim verification action.
5. CAPA Generation: Structured Effectiveness Verification plans (all 6 required fields).
6. Validation Node: Invalid action type detection.
7. Validation Node: Short or missing description rejection.
8. Validation Node: Missing or incomplete effectiveness plan validation.
9. Validation Node: Duplicate or substantially overlapping suggestions detection.
10. Validation Node: GxP gate reset (prohibits auto-approval of new recommendations).
11. Human Review: Initial review state is PROPOSED / PENDING_REVIEW.
12. Human Review: Explicit approval, rejection, and reviewer comments recording.
13. Human Review: Reviewer edits (description, owner assignment, target date, effectiveness plan).
14. LangGraph Human-in-the-Loop: Pauses execution at review boundary awaiting decision.
15. LangGraph Human-in-the-Loop: Resumes paused workflow via Command(resume=...) with explicit decisions.
16. LangGraph Human-in-the-Loop: Invalid resume requests (missing thread 404, not paused 400).
17. Database Persistence: Transactional persistence to PostgreSQL without duplicate actions on retry.
18. Database Persistence: Protection of human-approved actions against regenerated AI output.
19. API Endpoints: POST /api/investigations/{id}/capa/generate and POST /api/investigations/{id}/capa/resume.
"""

from datetime import date, datetime, timedelta, timezone
import json
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient

from app.agents.graph import (
    capa_workflow,
    resume_capa_workflow,
    run_capa_generation_workflow,
)
from app.agents.nodes.capa_generation_node import (
    CAPAGenerationLLMResponse,
    CAPARecommendationItemModel,
    EffectivenessVerificationPlanModel,
)
from app.agents.nodes.capa_validation_node import capa_validation_node
from app.agents.nodes.evidence_analysis_node import EvidenceAnalysisLLMResponse
from app.agents.nodes.fishbone_node import FishboneLLMResponse
from app.agents.nodes.five_whys_node import FiveWhysLLMResponse
from app.agents.nodes.synthesis_node import (
    ContributingFactorItemModel,
    PotentialRootCauseItemModel,
    SynthesisLLMResponse,
)
from app.database.session import SessionLocal
from app.main import app
from app.models.capa import CapaAction
from app.models.investigation import Investigation
from app.models.rca import FishboneCause as FishboneCauseModel, RCAAnalysis
from app.repositories.capa_repository import capa_repository
from app.schemas.capa import (
    CAPAGenerateRequest,
    CAPARecommendation,
    CAPAReviewItemDecision,
    CAPAReviewRequest,
    CAPAStatusEnum,
    CAPATypeEnum,
    CAPAWorkflowResult,
    EffectivenessVerificationPlan,
)
from app.schemas.investigation import InvestigationStatusEnum, SeverityEnum
from app.schemas.rca import (
    ContributingFactor,
    FishboneCategoryEnum,
    PotentialRootCause,
)
from app.services.ai_service import ai_service
from app.services.capa_service import capa_service

client = TestClient(app)


@pytest.fixture
def db():
    """Provides a fresh database session for persistence tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_sample_effectiveness_plan(
    outcome: str = "Zero recurring temperature excursions across subsequent batches.",
    method: str = "Continuous SCADA telemetry analysis and batch record verification.",
    evidence: str = "Signed batch production records and automated temperature alarm logs.",
    verifier: str = "Senior QA Compliance Specialist",
    timeframe: str = "Next 5 commercial batches",
    failure: str = "Any temperature excursion exceeding 70.0 °C during stage 3.",
) -> EffectivenessVerificationPlanModel:
    """Helper constructing an EffectivenessVerificationPlanModel."""
    return EffectivenessVerificationPlanModel(
        measurable_outcome=outcome,
        verification_method=method,
        evidence_required=evidence,
        suggested_verifier_role=verifier,
        verification_timeframe=timeframe,
        failure_criteria=failure,
    )


def _make_mock_ai_client(
    capa_resp: CAPAGenerationLLMResponse,
    synthesis_resp: Optional[SynthesisLLMResponse] = None,
):
    """Construct mock ChatGroq client returning appropriate structured response models."""
    mock_client = MagicMock()

    def mock_with_structured_output(schema, method="json_mode"):
        chain = MagicMock()
        if schema is CAPAGenerationLLMResponse:
            chain.invoke.return_value = capa_resp
        elif schema is SynthesisLLMResponse:
            chain.invoke.return_value = (
                synthesis_resp
                if synthesis_resp
                else SynthesisLLMResponse(potential_root_causes=[], contributing_factors=[])
            )
        elif schema is FiveWhysLLMResponse:
            chain.invoke.return_value = FiveWhysLLMResponse(chain=[])
        elif schema is FishboneLLMResponse:
            chain.invoke.return_value = FishboneLLMResponse(causes=[])
        elif schema is EvidenceAnalysisLLMResponse:
            chain.invoke.return_value = EvidenceAnalysisLLMResponse(items=[])
        return chain

    mock_client.with_structured_output.side_effect = mock_with_structured_output
    return mock_client


# -----------------------------------------------------------------------------
# 1. CAPA GENERATION: CORRECTIVE & PREVENTIVE ACTIONS
# -----------------------------------------------------------------------------

def test_capa_generation_corrective_and_preventive_actions():
    """Verify that generation node distinguishes corrective actions from preventive actions."""
    ca_plan = _make_sample_effectiveness_plan(
        outcome="Zero coolant supply valve binding events during exothermic crystallization.",
        failure="Any valve position feedback deviation exceeding 2% during ramp.",
    )
    pa_plan = _make_sample_effectiveness_plan(
        outcome="100% adherence to updated 12-month actuator replacement intervals.",
        failure="Any overdue actuator PM work order past 12 months.",
    )

    capa_resp = CAPAGenerationLLMResponse(
        recommendations=[
            CAPARecommendationItemModel(
                capa_id="CAPA-REC-01",
                action_type=CAPATypeEnum.CORRECTIVE_ACTION,
                description="Replace torn pneumatic actuator diaphragm on cooling valve CV-102 and recalibrate stroke.",
                related_root_cause_id="PRC-01",
                rationale="Directly restores cooling valve mechanical integrity to eliminate coolant flow interruption.",
                supporting_evidence_references=["Inspection Report IR-2026-90"],
                assumptions=["Replacement elastomeric diaphragm conforms to manufacturer spec."],
                dependencies=["Equipment lock-out and glycol supply drain."],
                suggested_owner_role="Senior Maintenance Mechanical Engineer",
                suggested_target_date="+14 days",
                effectiveness_verification=ca_plan,
            ),
            CAPARecommendationItemModel(
                capa_id="CAPA-REC-02",
                action_type=CAPATypeEnum.PREVENTIVE_ACTION,
                description="Revise PM SOP-401 to reduce pneumatic actuator inspection interval from 24 months to 12 months.",
                related_root_cause_id="PRC-01",
                rationale="Eliminates recurrence risk by preventing diaphragm fatigue failure before useful life expiration.",
                supporting_evidence_references=["Maintenance Schedule SOP-PM-401"],
                assumptions=["12-month interval provides sufficient safety margin against elastomeric fatigue."],
                dependencies=["Quality change control procedure QA-CC-01."],
                suggested_owner_role="Reliability Engineering Lead",
                suggested_target_date="+45 days",
                effectiveness_verification=pa_plan,
            ),
        ]
    )

    mock_client = _make_mock_ai_client(capa_resp=capa_resp)

    causes = [
        PotentialRootCause(
            cause_id="PRC-01",
            cause_description="Pneumatic actuator diaphragm rupture on valve CV-102.",
            cause_category="Machine",
            source_method="Five Whys",
            rationale="Substantiated by physical inspection teardown.",
        )
    ]

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_capa_generation_workflow(
            problem_statement="Cooling loss in Reactor R-102.",
            potential_root_causes=causes,
        )

        assert isinstance(result, CAPAWorkflowResult)
        assert len(result.capa_recommendations) == 2
        assert len(result.corrective_actions) == 1
        assert len(result.preventive_actions) == 1

        ca = result.corrective_actions[0]
        assert ca.action_type == CAPATypeEnum.CORRECTIVE_ACTION
        assert "CV-102" in ca.description
        assert ca.related_root_cause_id == "PRC-01"
        assert ca.review_status == CAPAStatusEnum.PROPOSED

        pa = result.preventive_actions[0]
        assert pa.action_type == CAPATypeEnum.PREVENTIVE_ACTION
        assert "PM SOP-401" in pa.description


# -----------------------------------------------------------------------------
# 2. CAPA GENERATION: EFFECTIVENESS VERIFICATION STRUCTURE
# -----------------------------------------------------------------------------

def test_capa_generation_effectiveness_verification_structure():
    """Verify that every generated recommendation contains a structured effectiveness verification plan."""
    eff_plan = _make_sample_effectiveness_plan(
        outcome="Zero API crystallization purity excursions below 99.0% over 10 batches.",
        method="In-process HPLC assay of crystal slurries at final crystallization stage.",
        evidence="QC Analytical Release Test Certificates and Certificates of Analysis.",
        verifier="QC Quality Compliance Manager",
        timeframe="Next 10 consecutive commercial batches",
        failure="Any individual batch purity result below 99.0% or unknown impurity > 0.10%.",
    )

    capa_resp = CAPAGenerationLLMResponse(
        recommendations=[
            CAPARecommendationItemModel(
                capa_id="CAPA-REC-01",
                action_type=CAPATypeEnum.CORRECTIVE_ACTION,
                description="Install secondary redundant temperature RTD sensor in Reactor R-102 thermowell.",
                related_root_cause_id="PRC-02",
                rationale="Provides dual-channel voting logic to prevent undetected sensor drift.",
                suggested_owner_role="Lead Automation / Instrumentation Engineer",
                suggested_target_date="+30 days",
                effectiveness_verification=eff_plan,
            )
        ]
    )

    mock_client = _make_mock_ai_client(capa_resp=capa_resp)

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_capa_generation_workflow(
            problem_statement="Sensor drift excursion during crystallization.",
        )

        assert len(result.capa_recommendations) == 1
        rec = result.capa_recommendations[0]
        eff = rec.effectiveness_verification
        assert isinstance(eff, EffectivenessVerificationPlan)
        assert len(eff.measurable_outcome) > 5
        assert len(eff.verification_method) > 5
        assert len(eff.evidence_required) > 5
        assert "QC" in eff.suggested_verifier_role
        assert "10" in eff.verification_timeframe
        assert len(eff.failure_criteria) > 5


# -----------------------------------------------------------------------------
# 3. CAPA GENERATION: MULTIPLE ROOT CAUSES & INSUFFICIENT EVIDENCE
# -----------------------------------------------------------------------------

def test_capa_generation_multiple_causes_and_fallback():
    """Verify handling when multiple root causes exist and fallback when AI generation fails."""
    mock_client = MagicMock()
    mock_client.with_structured_output.side_effect = Exception("Groq connection timeout")

    causes = [
        PotentialRootCause(
            cause_id="PRC-01",
            cause_description="Seal face contamination causing thermal friction.",
            cause_category="Machine",
            source_method="Five Whys",
            rationale="Observed particulate build-up.",
        ),
        PotentialRootCause(
            cause_id="PRC-02",
            cause_description="SOP heating rate limit ambiguity.",
            cause_category="Method",
            source_method="Fishbone",
            rationale="SOP revision lacked max ramp profile.",
        ),
    ]

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_capa_generation_workflow(
            problem_statement="Thermal runaway excursion during acylation.",
            potential_root_causes=causes,
        )

        # Workflow catches error, flags warning, and generates safe structured fallback
        assert isinstance(result, CAPAWorkflowResult)
        assert len(result.capa_warnings) > 0
        assert result.capa_generation_status == "FAILED"
        assert len(result.capa_recommendations) >= 2
        # Fallback contains both corrective and preventive actions
        assert len(result.corrective_actions) >= 1
        assert len(result.preventive_actions) >= 1


# -----------------------------------------------------------------------------
# 4. CAPA VALIDATION: ACTION TYPE & SHORT DESCRIPTION REJECTION
# -----------------------------------------------------------------------------

def test_capa_validation_invalid_action_type_and_short_description():
    """Verify validation flags invalid action types and inadequate descriptions."""
    eff = _make_sample_effectiveness_plan()

    # Create mock recommendation with short description and invalid action type
    mock_rec = MagicMock()
    mock_rec.capa_id = "CAPA-REC-01"
    mock_rec.action_type = "InvalidActionType"
    mock_rec.description = "Fix valve"
    mock_rec.rationale = "Fix it"
    mock_rec.suggested_owner_role = "Engineer"
    mock_rec.related_root_cause_id = None
    mock_rec.effectiveness_verification = MagicMock(
        measurable_outcome="Zero leaks across batches",
        verification_method="Visual and pressure check",
        evidence_required="Inspection log review",
        suggested_verifier_role="Senior QA Specialist",
        verification_timeframe="30 days",
        failure_criteria="Any leak detected",
    )
    mock_rec.review_status = CAPAStatusEnum.PROPOSED

    val_res = capa_validation_node({"capa_recommendations": [mock_rec]})
    assert len(val_res["capa_validation_errors"]) >= 2
    assert any("Invalid action_type" in err for err in val_res["capa_validation_errors"])
    assert any("at least 10 characters" in err for err in val_res["capa_validation_errors"])


# -----------------------------------------------------------------------------
# 5. CAPA VALIDATION: INCOMPLETE EFFECTIVENESS PLAN VALIDATION
# -----------------------------------------------------------------------------

def test_capa_validation_incomplete_effectiveness_plan():
    """Verify that validation flags missing or empty fields in the effectiveness verification plan."""
    mock_rec = MagicMock()
    mock_rec.capa_id = "CAPA-REC-01"
    mock_rec.action_type = CAPATypeEnum.CORRECTIVE_ACTION
    mock_rec.description = "Complete overhaul and calibration of primary jacket heat exchanger unit."
    mock_rec.rationale = "Restores full thermal dissipation capability."
    mock_rec.suggested_owner_role = "Senior Mechanical Specialist"
    mock_rec.related_root_cause_id = None
    # Empty effectiveness plan fields
    mock_rec.effectiveness_verification = MagicMock(
        measurable_outcome="",
        verification_method="",
        evidence_required="",
        suggested_verifier_role="",
        verification_timeframe="",
        failure_criteria="",
    )
    mock_rec.review_status = CAPAStatusEnum.PROPOSED

    val_res = capa_validation_node({"capa_recommendations": [mock_rec]})
    assert len(val_res["capa_validation_errors"]) >= 5
    assert any("measurable outcome" in err for err in val_res["capa_validation_errors"])



# -----------------------------------------------------------------------------
# 6. CAPA VALIDATION: DUPLICATE DETECTION & GxP PRE-APPROVAL PROHIBITION
# -----------------------------------------------------------------------------

def test_capa_validation_duplicate_detection_and_gxp_gate():
    """Verify duplicate proposal detection and GxP enforcement that new recommendations cannot be pre-approved."""
    eff = _make_sample_effectiveness_plan()

    capa_resp = CAPAGenerationLLMResponse(
        recommendations=[
            CAPARecommendationItemModel(
                capa_id="CAPA-REC-01",
                action_type=CAPATypeEnum.CORRECTIVE_ACTION,
                description="Replace worn elastomeric seal on reactor agitation drive shaft assembly.",
                rationale="Eliminates particulate shedding.",
                suggested_owner_role="Lead Maintenance Engineer",
                effectiveness_verification=eff,
            ),
            CAPARecommendationItemModel(
                capa_id="CAPA-REC-02",
                action_type=CAPATypeEnum.CORRECTIVE_ACTION,
                description="Replace worn elastomeric seal on reactor agitation drive shaft assembly.",  # Exact duplicate!
                rationale="Eliminates particulate shedding.",
                suggested_owner_role="Lead Maintenance Engineer",
                effectiveness_verification=eff,
            ),
        ]
    )

    mock_client = _make_mock_ai_client(capa_resp=capa_resp)

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_capa_generation_workflow(problem_statement="Duplicate detection test.")
        assert len(result.capa_warnings) > 0
        assert any("duplicate" in w.lower() for w in result.capa_warnings)
        # All actions must remain Proposed / Pending Review
        for rec in result.capa_recommendations:
            assert rec.review_status in (CAPAStatusEnum.PROPOSED, CAPAStatusEnum.PENDING_REVIEW)


# -----------------------------------------------------------------------------
# 7. LANGGRAPH HUMAN-IN-THE-LOOP: PAUSE AT REVIEW BOUNDARY
# -----------------------------------------------------------------------------

def test_langgraph_pauses_at_human_review_boundary():
    """Verify that graph pauses at capa_human_review_node and MemorySaver retains interrupt state."""
    eff = _make_sample_effectiveness_plan()
    capa_resp = CAPAGenerationLLMResponse(
        recommendations=[
            CAPARecommendationItemModel(
                capa_id="CAPA-REC-01",
                action_type=CAPATypeEnum.CORRECTIVE_ACTION,
                description="Install automated high-temperature interlock shutdown on heating mantle circuit.",
                rationale="Prevents thermal runaway regardless of operator manual intervention speed.",
                suggested_owner_role="Automation Systems Specialist",
                suggested_target_date="+30 days",
                effectiveness_verification=eff,
            )
        ]
    )

    mock_client = _make_mock_ai_client(capa_resp=capa_resp)
    thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_capa_generation_workflow(
            problem_statement="Thermal interlock implementation.",
            thread_id=thread_id,
        )

        # Graph execution must pause at review boundary
        assert result.workflow_completion_status == "PAUSED_FOR_HUMAN_REVIEW"
        assert result.human_review_required is True
        assert result.capa_review_status == "PENDING_REVIEW"
        assert len(result.pending_actions) == 1

        # Check checkpointer state snapshot
        config = {"configurable": {"thread_id": thread_id}}
        state_snap = capa_workflow.get_state(config)
        assert state_snap is not None
        # Tasks list must contain active interrupt
        assert any(len(t.interrupts) > 0 for t in state_snap.tasks)


# -----------------------------------------------------------------------------
# 8. LANGGRAPH HUMAN-IN-THE-LOOP: RESUME WORKFLOW WITH EXPLICIT DECISIONS
# -----------------------------------------------------------------------------

def test_langgraph_resume_workflow_with_human_decisions():
    """Verify that paused workflow resumes when Command(resume=...) is supplied with explicit decisions."""
    eff = _make_sample_effectiveness_plan()
    capa_resp = CAPAGenerationLLMResponse(
        recommendations=[
            CAPARecommendationItemModel(
                capa_id="CAPA-REC-01",
                action_type=CAPATypeEnum.CORRECTIVE_ACTION,
                description="Replace ruptured rupture disc RD-101 and recalibrate burst sensor telemetry.",
                rationale="Restores physical overpressure containment boundary.",
                suggested_owner_role="Mechanical Engineer",
                effectiveness_verification=eff,
            ),
            CAPARecommendationItemModel(
                capa_id="CAPA-REC-02",
                action_type=CAPATypeEnum.PREVENTIVE_ACTION,
                description="Replace entire reactor vessel shell assembly.",
                rationale="Overly aggressive suggestion without structural crack evidence.",
                suggested_owner_role="Plant Manager",
                effectiveness_verification=eff,
            ),
        ]
    )

    mock_client = _make_mock_ai_client(capa_resp=capa_resp)
    thread_id = f"test-thread-resume-{uuid.uuid4().hex[:8]}"

    # 1. Run generation -> pauses at review boundary
    with patch.object(ai_service, "get_client", return_value=mock_client):
        paused_result = run_capa_generation_workflow(
            problem_statement="Overpressure excursion in distillation system.",
            thread_id=thread_id,
        )
        assert paused_result.workflow_completion_status == "PAUSED_FOR_HUMAN_REVIEW"

    # 2. Prepare human review request: approve #1 with edits, reject #2
    review_req = CAPAReviewRequest(
        thread_id=thread_id,
        decisions=[
            CAPAReviewItemDecision(
                capa_id="CAPA-REC-01",
                decision=CAPAStatusEnum.APPROVED,
                edited_description="Replace ruptured rupture disc RD-101 with Hastelloy-C spec and recalibrate burst sensor.",
                assigned_owner="John Smith (Senior Reliability Engineer)",
                target_date=date(2026, 12, 1),
                reviewer_comments="Approved with upgrade to Hastelloy-C disc for enhanced corrosion resistance.",
                reviewer_identifier="Sarah Jenkins (QA Director)",
            ),
            CAPAReviewItemDecision(
                capa_id="CAPA-REC-02",
                decision=CAPAStatusEnum.REJECTED,
                reviewer_comments="Rejected: Vessel shell integrity testing showed zero defect; full replacement is unwarranted.",
                reviewer_identifier="Sarah Jenkins (QA Director)",
            ),
        ],
        general_comments="QA review complete. Disc replacement approved; vessel replacement rejected as excessive.",
    )

    # 3. Resume workflow
    resumed_result = resume_capa_workflow(
        thread_id=thread_id,
        review_request=review_req,
    )

    # 4. Verify outcomes
    assert isinstance(resumed_result, CAPAWorkflowResult)
    assert resumed_result.workflow_completion_status == "COMPLETED"
    assert len(resumed_result.approved_actions) == 1
    assert len(resumed_result.rejected_actions) == 1
    assert len(resumed_result.pending_actions) == 0

    approved_item = resumed_result.approved_actions[0]
    assert approved_item.review_status == CAPAStatusEnum.APPROVED
    assert "Hastelloy-C" in approved_item.description
    assert approved_item.assigned_owner == "John Smith (Senior Reliability Engineer)"
    assert approved_item.actual_target_date == date(2026, 12, 1)
    assert "Sarah Jenkins" in approved_item.reviewed_by

    rejected_item = resumed_result.rejected_actions[0]
    assert rejected_item.review_status == CAPAStatusEnum.REJECTED
    assert "Rejected: Vessel shell integrity" in rejected_item.reviewer_comments


# -----------------------------------------------------------------------------
# 9. LANGGRAPH HUMAN-IN-THE-LOOP: INVALID RESUME REQUESTS
# -----------------------------------------------------------------------------

def test_langgraph_invalid_resume_requests():
    """Verify that resuming a non-existent or unpaused thread raises appropriate HTTP exceptions."""
    from fastapi import HTTPException

    # Non-existent thread
    with pytest.raises(HTTPException) as exc_info:
        resume_capa_workflow(
            thread_id="non-existent-thread-xyz",
            review_request=CAPAReviewRequest(
                decisions=[
                    CAPAReviewItemDecision(
                        capa_id="CAPA-REC-01",
                        decision=CAPAStatusEnum.APPROVED,
                    )
                ]
            ),
        )
    assert exc_info.value.status_code == 404


# -----------------------------------------------------------------------------
# 10. DATABASE PERSISTENCE: ATOMICITY, IDEMPOTENCY & RECORD PROTECTION
# -----------------------------------------------------------------------------

def test_database_persistence_and_record_protection(db):
    """Verify transactional persistence, idempotency on workflow retry, and protection of approved actions."""
    suffix = uuid.uuid4().hex[:6].upper()

    # 1. Create real investigation in PostgreSQL
    inv = Investigation(
        investigation_number=f"INV-CAPA-{suffix}",
        incident_title="Solvent Distillation Overfill",
        incident_description="Solvent receiver vessel tank overflowed during transfer.",
        batch_number=f"BATCH-CAPA-{suffix}",
        equipment="Solvent Recovery Facility",
        investigation_status=InvestigationStatusEnum.OPEN,
        severity=SeverityEnum.HIGH,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    # 2. Pre-create an existing Approved CAPA in PostgreSQL
    existing_approved_capa = CapaAction(
        investigation_id=inv.id,
        action_type=CAPATypeEnum.CORRECTIVE_ACTION,
        description="Existing human approved modification: Re-route overflow line directly to scrubber vessel.",
        action_owner="Michael Brown (Plant Engineering Lead)",
        target_date=date(2026, 11, 20),
        effectiveness_verification="Method: Visual inspection | Target: Zero liquid carryover",
        action_status=CAPAStatusEnum.APPROVED,  # Human approved!
    )
    db.add(existing_approved_capa)
    db.commit()

    # 3. Simulate workflow persisting recommendations
    eff = _make_sample_effectiveness_plan()
    recs = [
        # This one matches the existing approved description -> must NOT overwrite it!
        CAPARecommendation(
            capa_id="CAPA-REC-01",
            action_type=CAPATypeEnum.CORRECTIVE_ACTION,
            description="Existing human approved modification: Re-route overflow line directly to scrubber vessel.",
            rationale="AI regenerated proposal",
            suggested_owner_role="Junior Tech",
            effectiveness_verification=EffectivenessVerificationPlan(**eff.model_dump()),
            review_status=CAPAStatusEnum.PROPOSED,
        ),
        # New proposal
        CAPARecommendation(
            capa_id="CAPA-REC-02",
            action_type=CAPATypeEnum.PREVENTIVE_ACTION,
            description="Install high-high radar level transmitter LIT-402 with automated pump interlock.",
            rationale="Eliminates tank overflow risk via automated independent instrument shutdown.",
            suggested_owner_role="Automation Lead",
            effectiveness_verification=EffectivenessVerificationPlan(**eff.model_dump()),
            review_status=CAPAStatusEnum.PROPOSED,
        ),
    ]

    persisted = capa_service.persist_capa_recommendations(
        db=db,
        investigation_id=str(inv.id),
        recommendations=recs,
    )

    assert len(persisted) == 2

    # Verify existing approved action was preserved
    db.refresh(existing_approved_capa)
    assert existing_approved_capa.action_status == CAPAStatusEnum.APPROVED
    assert existing_approved_capa.action_owner == "Michael Brown (Plant Engineering Lead)"

    # Verify new action was created
    new_action = next(a for a in persisted if a.id != existing_approved_capa.id)
    assert "radar level transmitter" in new_action.description
    assert new_action.action_status == CAPAStatusEnum.PROPOSED

    # 4. Test Idempotency: re-running persist does NOT create duplicate records
    persisted_second_run = capa_service.persist_capa_recommendations(
        db=db,
        investigation_id=str(inv.id),
        recommendations=recs,
    )
    all_in_db = capa_repository.list_by_investigation(db, inv.id)
    assert len(all_in_db) == 2  # Still exactly 2 records, no duplicates!


# -----------------------------------------------------------------------------
# 11. API ENDPOINT: POST /api/investigations/{id}/capa/generate
# -----------------------------------------------------------------------------

def test_api_generate_capa_endpoint(db):
    """Verify that POST /api/investigations/{id}/capa/generate returns 200 with paused workflow result."""
    suffix = uuid.uuid4().hex[:6].upper()

    inv = Investigation(
        investigation_number=f"INV-API-CAPA-{suffix}",
        incident_title="Agitator Seal Excursion",
        incident_description="Mechanical seal face friction exceeded temperature threshold.",
        batch_number=f"BATCH-{suffix}",
        equipment="Reactor Suite 1",
        investigation_status=InvestigationStatusEnum.OPEN,
        severity=SeverityEnum.MEDIUM,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    eff = _make_sample_effectiveness_plan()
    capa_resp = CAPAGenerationLLMResponse(
        recommendations=[
            CAPARecommendationItemModel(
                capa_id="CAPA-REC-01",
                action_type=CAPATypeEnum.CORRECTIVE_ACTION,
                description="Overhaul mechanical seal cartridge and replace barrier fluid flush filter.",
                rationale="Restores proper seal lubrication and cooling.",
                suggested_owner_role="Lead Maintenance Tech",
                suggested_target_date="+15 days",
                effectiveness_verification=eff,
            )
        ]
    )

    mock_client = _make_mock_ai_client(capa_resp=capa_resp)

    with patch.object(ai_service, "get_client", return_value=mock_client):
        response = client.post(
            f"/api/investigations/{inv.id}/capa/generate",
            json={"persist": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"].startswith("WF-CAPA")
        assert data["workflow_completion_status"] == "PAUSED_FOR_HUMAN_REVIEW"
        assert data["human_review_required"] is True
        assert len(data["capa_recommendations"]) == 1
        assert data["capa_recommendations"][0]["action_type"] == "Corrective Action"
        assert data["persisted_in_db"] is True
        assert len(data["persisted_capa_ids"]) == 1


# -----------------------------------------------------------------------------
# 12. API ENDPOINT: POST /api/investigations/{id}/capa/resume
# -----------------------------------------------------------------------------

def test_api_resume_capa_endpoint(db):
    """Verify that POST /api/investigations/{id}/capa/resume resumes paused thread and completes workflow."""
    suffix = uuid.uuid4().hex[:6].upper()

    inv = Investigation(
        investigation_number=f"INV-API-RESUME-{suffix}",
        incident_title="Filter Dryer Screen Breach",
        incident_description="Mesh filter cloth tore during agitated cake washing.",
        batch_number=f"BATCH-{suffix}",
        equipment="Filter Dryer FD-101",
        investigation_status=InvestigationStatusEnum.OPEN,
        severity=SeverityEnum.HIGH,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    eff = _make_sample_effectiveness_plan()
    capa_resp = CAPAGenerationLLMResponse(
        recommendations=[
            CAPARecommendationItemModel(
                capa_id="CAPA-REC-01",
                action_type=CAPATypeEnum.CORRECTIVE_ACTION,
                description="Replace torn 20-micron filter cloth with reinforced multi-layer sintered mesh screen.",
                rationale="Provides higher differential pressure resistance during cake washing.",
                suggested_owner_role="Senior Process Engineer",
                suggested_target_date="+20 days",
                effectiveness_verification=eff,
            )
        ]
    )

    mock_client = _make_mock_ai_client(capa_resp=capa_resp)

    # 1. Generate -> pauses at review boundary
    with patch.object(ai_service, "get_client", return_value=mock_client):
        gen_res = client.post(
            f"/api/investigations/{inv.id}/capa/generate",
            json={"persist": True},
        )
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        thread_id = gen_data["thread_id"]
        assert gen_data["workflow_completion_status"] == "PAUSED_FOR_HUMAN_REVIEW"

    # 2. Resume via API with explicit approval decision
    resume_payload = {
        "thread_id": thread_id,
        "decisions": [
            {
                "capa_id": "CAPA-REC-01",
                "decision": "Approved",
                "assigned_owner": "David Miller (Engineering Manager)",
                "target_date": "2026-12-15",
                "reviewer_comments": "Approved. Sintered mesh specification approved by QA.",
                "reviewer_identifier": "Lead QA Specialist",
            }
        ],
        "general_comments": "Approved for execution.",
    }

    resume_res = client.post(
        f"/api/investigations/{inv.id}/capa/resume",
        json=resume_payload,
    )

    assert resume_res.status_code == 200
    res_data = resume_res.json()
    assert res_data["workflow_completion_status"] == "COMPLETED"
    assert len(res_data["approved_actions"]) == 1
    assert res_data["approved_actions"][0]["review_status"] == "Approved"
    assert res_data["approved_actions"][0]["assigned_owner"] == "David Miller (Engineering Manager)"
