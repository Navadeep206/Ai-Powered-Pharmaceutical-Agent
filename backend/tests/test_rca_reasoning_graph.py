"""Comprehensive Automated Test Suite for RootIQ RCA Reasoning Engine (Step 06 Phase 2).

Verifies the complete AI-assisted LangGraph RCA workflow:
1. Five Whys: valid sequential chain (sequential 1..N, terminal root cause).
2. Five Whys: incomplete chain early stop without artificial padding.
3. Five Whys: unsupported inference handling & uncertainty notes.
4. Five Whys: evidence references & status mapping.
5. Fishbone: 6M category mapping.
6. Fishbone: empty categories when unsupported by facts.
7. Fishbone: multiple causes per category.
8. Evidence Analysis: supporting vs contradictory classification.
9. Evidence Analysis: missing evidence and investigator questions identification.
10. Synthesis: multiple candidate root causes & secondary contributing factors.
11. Synthesis: human review preservation (no auto-confirming root causes; human_review_required=True).
12. Workflow error handling: partial results on Groq failure/timeout.
13. Database persistence: atomic persistence without overwriting human-reviewed records.
14. API endpoint: POST /api/investigations/{investigation_id}/rca/generate.
"""

import json
import uuid
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.agents.graph import (
    build_rca_reasoning_graph,
    rca_reasoning_workflow,
    run_rca_reasoning_workflow,
)
from app.agents.nodes.evidence_analysis_node import (
    EvidenceAnalysisLLMResponse,
    EvidenceItemModel,
)
from app.agents.nodes.fishbone_node import (
    FishboneCauseItemModel,
    FishboneLLMResponse,
)
from app.agents.nodes.five_whys_node import (
    FiveWhysItemModel,
    FiveWhysLLMResponse,
)
from app.agents.nodes.synthesis_node import (
    ContributingFactorItemModel,
    PotentialRootCauseItemModel,
    SynthesisLLMResponse,
)
from app.core.exceptions import AITimeoutError
from app.database.session import SessionLocal
from app.main import app
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.rca import FishboneCause as FishboneCauseModel, FiveWhy, RCAAnalysis
from app.schemas.evidence import EvidenceTypeEnum
from app.schemas.investigation import InvestigationStatusEnum, SeverityEnum
from app.schemas.rca import (
    CauseVerificationStatusEnum,
    EvidenceAssessment,
    FishboneCategoryEnum,
    FishboneCause,
    FiveWhysLevel,
    RCAGenerateRequest,
    RCAWorkflowResult,
)
from app.services.ai_service import ai_service
from app.services.rca_service import rca_service

client = TestClient(app)


@pytest.fixture
def db():
    """Provides a fresh database session for persistence tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_mock_client(
    five_whys_resp: FiveWhysLLMResponse,
    fishbone_resp: FishboneLLMResponse,
    evidence_resp: EvidenceAnalysisLLMResponse,
    synthesis_resp: SynthesisLLMResponse,
):
    """Construct a mock ChatGroq client returning appropriate response models by schema."""
    mock_client = MagicMock()

    def mock_with_structured_output(schema, method="json_mode"):
        chain = MagicMock()
        if schema is FiveWhysLLMResponse:
            chain.invoke.return_value = five_whys_resp
        elif schema is FishboneLLMResponse:
            chain.invoke.return_value = fishbone_resp
        elif schema is EvidenceAnalysisLLMResponse:
            chain.invoke.return_value = evidence_resp
        elif schema is SynthesisLLMResponse:
            chain.invoke.return_value = synthesis_resp
        return chain

    mock_client.with_structured_output.side_effect = mock_with_structured_output
    return mock_client


# -----------------------------------------------------------------------------
# 1. FIVE WHYS: VALID SEQUENTIAL CHAIN
# -----------------------------------------------------------------------------

def test_five_whys_valid_sequential_chain():
    """Verify that Five Whys generates strictly sequential levels 1..N with a terminal root cause."""
    whys_llm = FiveWhysLLMResponse(
        chain=[
            FiveWhysItemModel(
                level=1,
                question="Why did reactor R-102 temperature exceed 70.0 °C?",
                answer="Glycol coolant flow rate to the reactor jacket dropped below required minimum.",
                reasoning="Telemetry shows flow meter FM-102 dropped to 0 LPM.",
                supporting_evidence_references=["SCADA Tag FM-102"],
                confidence=0.95,
                is_root_cause=False,
            ),
            FiveWhysItemModel(
                level=2,
                question="Why did glycol coolant flow rate drop?",
                answer="Cooling supply valve CV-102 failed to open during exothermic transition.",
                reasoning="Actuator signal commanded open but stem position remained closed.",
                supporting_evidence_references=["SCADA Tag ZS-102", "Maintenance Log #4401"],
                confidence=0.92,
                is_root_cause=False,
            ),
            FiveWhysItemModel(
                level=3,
                question="Why did cooling supply valve CV-102 fail to open?",
                answer="Pneumatic actuator diaphragm experienced mechanical tear from fatigue.",
                reasoning="Physical inspection revealed 12mm radial rupture in elastomeric diaphragm.",
                supporting_evidence_references=["Inspection Report IR-2026-90"],
                confidence=0.98,
                is_root_cause=True,
            ),
        ]
    )

    mock_client = _make_mock_client(
        five_whys_resp=whys_llm,
        fishbone_resp=FishboneLLMResponse(causes=[]),
        evidence_resp=EvidenceAnalysisLLMResponse(items=[]),
        synthesis_resp=SynthesisLLMResponse(potential_root_causes=[], contributing_factors=[]),
    )

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_rca_reasoning_workflow(
            problem_statement="Thermal excursion in Reactor R-102 exceeding 70 °C limit.",
            incident_context={"equipment_id": "R-102", "batch_number": "BATCH-902"},
        )

        assert isinstance(result, RCAWorkflowResult)
        whys = result.five_whys_analysis
        assert len(whys) == 3

        # Verify strictly sequential levels
        for idx, w in enumerate(whys):
            assert w.level == idx + 1
            assert w.why_number == idx + 1
            assert len(w.question) > 5
            assert len(w.answer) > 5

        # Check terminal root cause
        assert whys[0].is_root_cause is False
        assert whys[1].is_root_cause is False
        assert whys[2].is_root_cause is True


# -----------------------------------------------------------------------------
# 2. FIVE WHYS: INCOMPLETE CHAIN EARLY STOP (NO ARTIFICIAL PADDING)
# -----------------------------------------------------------------------------

def test_five_whys_incomplete_chain_early_stop():
    """Verify that workflow halts when root cause is reached and does not pad with redundant steps."""
    whys_llm = FiveWhysLLMResponse(
        chain=[
            FiveWhysItemModel(
                level=1,
                question="Why was impurity level 0.22% above specification?",
                answer="Raw material intermediate lot LOT-8812 contained degraded precursor.",
                reasoning="Vendor Certificate of Analysis was audited against internal re-test assay.",
                supporting_evidence_references=["CoA LOT-8812"],
                confidence=0.96,
                is_root_cause=False,
            ),
            FiveWhysItemModel(
                level=2,
                question="Why did LOT-8812 contain degraded precursor?",
                answer="Vendor storage temperature during transit exceeded 25 °C cold-chain limit.",
                reasoning="Datalogger data recovered from shipping container confirmed 36-hour excursion.",
                supporting_evidence_references=["Transit Datalogger #TR-99"],
                confidence=0.99,
                is_root_cause=True,  # Root cause identified at level 2
            ),
        ]
    )

    mock_client = _make_mock_client(
        five_whys_resp=whys_llm,
        fishbone_resp=FishboneLLMResponse(causes=[]),
        evidence_resp=EvidenceAnalysisLLMResponse(items=[]),
        synthesis_resp=SynthesisLLMResponse(potential_root_causes=[], contributing_factors=[]),
    )

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_rca_reasoning_workflow(
            problem_statement="Out of specification impurity level in final API lot.",
        )

        whys = result.five_whys_analysis
        assert len(whys) == 2  # Exactly 2 levels, not padded to 5
        assert whys[1].is_root_cause is True
        assert whys[1].answer == "Vendor storage temperature during transit exceeded 25 °C cold-chain limit."


# -----------------------------------------------------------------------------
# 3. FIVE WHYS: UNSUPPORTED INFERENCE HANDLING & UNCERTAINTY NOTES
# -----------------------------------------------------------------------------

def test_five_whys_unsupported_inference_and_uncertainty():
    """Verify that inferential steps with missing data capture uncertainty notes."""
    whys_llm = FiveWhysLLMResponse(
        chain=[
            FiveWhysItemModel(
                level=1,
                question="Why did filtration time double from 2 hours to 4 hours?",
                answer="Filter cloth cake layer exhibited higher than normal hydraulic resistance.",
                reasoning="Filtration differential pressure rose to 3.2 bar.",
                supporting_evidence_references=["DP Sensor Trend"],
                confidence=0.90,
                is_root_cause=False,
            ),
            FiveWhysItemModel(
                level=2,
                question="Why did cake layer hydraulic resistance increase?",
                answer="Possible crystal polymorph shift or fine particle agglomeration during crystallization.",
                reasoning="Microscopic particle size distribution assay is currently pending.",
                supporting_evidence_references=[],
                confidence=0.65,
                uncertainty_notes="Assay pending; particle size distribution not yet confirmed by QC lab.",
                is_root_cause=True,
            ),
        ]
    )

    mock_client = _make_mock_client(
        five_whys_resp=whys_llm,
        fishbone_resp=FishboneLLMResponse(causes=[]),
        evidence_resp=EvidenceAnalysisLLMResponse(items=[]),
        synthesis_resp=SynthesisLLMResponse(potential_root_causes=[], contributing_factors=[]),
    )

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_rca_reasoning_workflow(
            problem_statement="Extended filtration cycle time during API isolation.",
        )

        whys = result.five_whys_analysis
        step2 = whys[1]
        assert step2.confidence == 0.65
        assert step2.uncertainty_notes is not None
        assert "Assay pending" in step2.uncertainty_notes
        assert step2.status == CauseVerificationStatusEnum.AI_SUGGESTION


# -----------------------------------------------------------------------------
# 4. FIVE WHYS: EVIDENCE CITATIONS & STATUS MAPPING
# -----------------------------------------------------------------------------

def test_five_whys_evidence_references_and_status():
    """Verify that cited evidence references promote status to Evidence Supported."""
    whys_llm = FiveWhysLLMResponse(
        chain=[
            FiveWhysItemModel(
                level=1,
                question="Why did agitation motor trip?",
                answer="Motor overload protection relay opened due to excessive current draw.",
                reasoning="Relay OCR-101 tripped at 42 Amps.",
                supporting_evidence_references=["Relay Trip Log OCR-101", "SCADA Event #8812"],
                confidence=0.99,
                is_root_cause=True,
            )
        ]
    )

    mock_client = _make_mock_client(
        five_whys_resp=whys_llm,
        fishbone_resp=FishboneLLMResponse(causes=[]),
        evidence_resp=EvidenceAnalysisLLMResponse(items=[]),
        synthesis_resp=SynthesisLLMResponse(potential_root_causes=[], contributing_factors=[]),
    )

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_rca_reasoning_workflow(
            problem_statement="Agitation motor tripped during dissolution.",
        )

        step = result.five_whys_analysis[0]
        assert len(step.supporting_evidence_references) == 2
        assert step.status == CauseVerificationStatusEnum.EVIDENCE_SUPPORTED


# -----------------------------------------------------------------------------
# 5. FISHBONE: 6M CATEGORY MAPPING
# -----------------------------------------------------------------------------

def test_fishbone_6m_category_mapping():
    """Verify that Fishbone causes map strictly to the Ishikawa 6M dimensions."""
    fishbone_llm = FishboneLLMResponse(
        causes=[
            FishboneCauseItemModel(
                cause_id="CAUSE-01",
                category=FishboneCategoryEnum.MACHINE,
                cause_description="Mechanical seal face friction caused local hot spot.",
                reasoning="Seal flush fluid was contaminated.",
                supporting_evidence_references=["Maintenance Log #102"],
                confidence=0.90,
            ),
            FishboneCauseItemModel(
                cause_id="CAUSE-02",
                category=FishboneCategoryEnum.METHOD,
                cause_description="Batch record did not specify maximum ramp rate for heating mantle.",
                reasoning="SOP revision 4 omitted specific heat-up profile.",
                supporting_evidence_references=["BMR-SOP-201"],
                confidence=0.88,
            ),
            FishboneCauseItemModel(
                cause_id="CAUSE-03",
                category=FishboneCategoryEnum.MEASUREMENT,
                cause_description="Resistance Temperature Detector (RTD) probe calibration had drifted by +2.4 °C.",
                reasoning="Post-incident calibration check verified offset.",
                supporting_evidence_references=["Calibration Cert #CAL-889"],
                confidence=0.95,
            ),
        ]
    )

    mock_client = _make_mock_client(
        five_whys_resp=FiveWhysLLMResponse(chain=[]),
        fishbone_resp=fishbone_llm,
        evidence_resp=EvidenceAnalysisLLMResponse(items=[]),
        synthesis_resp=SynthesisLLMResponse(potential_root_causes=[], contributing_factors=[]),
    )

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_rca_reasoning_workflow(
            problem_statement="Thermal control failure during crystallization.",
        )

        causes = result.fishbone_analysis
        assert len(causes) == 3
        categories = {c.category for c in causes}
        assert FishboneCategoryEnum.MACHINE in categories
        assert FishboneCategoryEnum.METHOD in categories
        assert FishboneCategoryEnum.MEASUREMENT in categories


# -----------------------------------------------------------------------------
# 6. FISHBONE: EMPTY CATEGORIES WHEN UNSUPPORTED
# -----------------------------------------------------------------------------

def test_fishbone_empty_categories_when_unsupported():
    """Verify that categories without supporting evidence remain empty rather than hallucinated."""
    # Only Machine and Method are supported; Environment, Manpower, Material, Measurement should have no causes
    fishbone_llm = FishboneLLMResponse(
        causes=[
            FishboneCauseItemModel(
                cause_id="CAUSE-01",
                category=FishboneCategoryEnum.MACHINE,
                cause_description="Chilled water circulating pump impeller cavitation.",
                confidence=0.91,
            )
        ]
    )

    mock_client = _make_mock_client(
        five_whys_resp=FiveWhysLLMResponse(chain=[]),
        fishbone_resp=fishbone_llm,
        evidence_resp=EvidenceAnalysisLLMResponse(items=[]),
        synthesis_resp=SynthesisLLMResponse(potential_root_causes=[], contributing_factors=[]),
    )

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_rca_reasoning_workflow(
            problem_statement="Cooling capacity loss during exothermic batch step.",
        )

        causes = result.fishbone_analysis
        assert len(causes) == 1
        assert causes[0].category == FishboneCategoryEnum.MACHINE

        # Verify Environment, Material, Manpower, Measurement are NOT populated
        categories = [c.category for c in causes]
        assert FishboneCategoryEnum.ENVIRONMENT not in categories
        assert FishboneCategoryEnum.MATERIAL not in categories
        assert FishboneCategoryEnum.MANPOWER not in categories


# -----------------------------------------------------------------------------
# 7. FISHBONE: MULTIPLE CAUSES PER CATEGORY
# -----------------------------------------------------------------------------

def test_fishbone_multiple_causes_per_category():
    """Verify that multiple causal factors can be mapped into the same Ishikawa category."""
    fishbone_llm = FishboneLLMResponse(
        causes=[
            FishboneCauseItemModel(
                cause_id="CAUSE-01",
                category=FishboneCategoryEnum.MACHINE,
                cause_description="Primary cooling valve diaphragm tear.",
                confidence=0.95,
            ),
            FishboneCauseItemModel(
                cause_id="CAUSE-02",
                category=FishboneCategoryEnum.MACHINE,
                cause_description="Auxiliary chiller bypass valve stuck at 30% position.",
                confidence=0.89,
            ),
        ]
    )

    mock_client = _make_mock_client(
        five_whys_resp=FiveWhysLLMResponse(chain=[]),
        fishbone_resp=fishbone_llm,
        evidence_resp=EvidenceAnalysisLLMResponse(items=[]),
        synthesis_resp=SynthesisLLMResponse(potential_root_causes=[], contributing_factors=[]),
    )

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_rca_reasoning_workflow(
            problem_statement="Cooling failure across redundant loops.",
        )

        causes = result.fishbone_analysis
        machine_causes = [c for c in causes if c.category == FishboneCategoryEnum.MACHINE]
        assert len(machine_causes) == 2
        assert machine_causes[0].cause_description == "Primary cooling valve diaphragm tear."
        assert machine_causes[1].cause_description == "Auxiliary chiller bypass valve stuck at 30% position."


# -----------------------------------------------------------------------------
# 8. EVIDENCE ANALYSIS: SUPPORTING VS CONTRADICTORY CLASSIFICATION
# -----------------------------------------------------------------------------

def test_evidence_supporting_vs_contradictory_classification():
    """Verify that empirical evidence is accurately partitioned into Supporting and Contradictory."""
    evidence_llm = EvidenceAnalysisLLMResponse(
        items=[
            EvidenceItemModel(
                evidence_id="EVD-001",
                evidence_description="SCADA trend shows jacket coolant flow reached 0 LPM at 04:12 UTC.",
                evidence_type=EvidenceTypeEnum.SUPPORTING,
                source_reference="SCADA Historian Tag FIT-102",
                related_potential_cause="Coolant Flow Interruption",
                confidence=0.99,
            ),
            EvidenceItemModel(
                evidence_id="EVD-002",
                evidence_description="Glycol reservoir supply pressure maintained at 4.2 bar normal operating limit.",
                evidence_type=EvidenceTypeEnum.CONTRADICTORY,
                source_reference="Utility Pressure Log PIT-01",
                related_potential_cause="Central Utility Pump Failure",
                reasoning="Contradicts hypothesis that the central utility plant failed.",
                confidence=0.96,
            ),
        ],
        missing_evidence=[],
        investigator_questions=[],
    )

    mock_client = _make_mock_client(
        five_whys_resp=FiveWhysLLMResponse(chain=[]),
        fishbone_resp=FishboneLLMResponse(causes=[]),
        evidence_resp=evidence_llm,
        synthesis_resp=SynthesisLLMResponse(potential_root_causes=[], contributing_factors=[]),
    )

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_rca_reasoning_workflow(
            problem_statement="Loss of cooling in reactor vessel.",
        )

        assessments = result.evidence_assessment
        assert len(assessments) == 2

        supporting = [e for e in assessments if e.evidence_type == EvidenceTypeEnum.SUPPORTING]
        contradictory = [e for e in assessments if e.evidence_type == EvidenceTypeEnum.CONTRADICTORY]

        assert len(supporting) == 1
        assert supporting[0].evidence_id == "EVD-001"
        assert supporting[0].source_reference == "SCADA Historian Tag FIT-102"

        assert len(contradictory) == 1
        assert contradictory[0].evidence_id == "EVD-002"
        assert "Contradicts hypothesis" in contradictory[0].reasoning


# -----------------------------------------------------------------------------
# 9. EVIDENCE ANALYSIS: MISSING EVIDENCE AND INVESTIGATOR QUESTIONS
# -----------------------------------------------------------------------------

def test_evidence_missing_evidence_and_investigator_questions():
    """Verify identification of documentation gaps and generation of targeted investigator inquiries."""
    evidence_llm = EvidenceAnalysisLLMResponse(
        items=[],
        missing_evidence=[
            "Preventive maintenance work order records for valve CV-102 from the past 12 months.",
            "Certificates of calibration for RTD temperature sensors TT-102A and TT-102B.",
        ],
        investigator_questions=[
            "When was the actuator diaphragm on valve CV-102 last inspected or replaced?",
            "Did the SCADA alarm system trigger at the preliminary 68 °C warning threshold?",
        ],
    )

    mock_client = _make_mock_client(
        five_whys_resp=FiveWhysLLMResponse(chain=[]),
        fishbone_resp=FishboneLLMResponse(causes=[]),
        evidence_resp=evidence_llm,
        synthesis_resp=SynthesisLLMResponse(potential_root_causes=[], contributing_factors=[]),
    )

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_rca_reasoning_workflow(
            problem_statement="Reactor thermal excursion excursion.",
        )

        assert len(result.missing_evidence) == 2
        assert "Preventive maintenance work order" in result.missing_evidence[0]

        assert len(result.investigator_questions) == 2
        assert "When was the actuator diaphragm" in result.investigator_questions[0]


# -----------------------------------------------------------------------------
# 10. SYNTHESIS: MULTIPLE CANDIDATE ROOT CAUSES & CONTRIBUTING FACTORS
# -----------------------------------------------------------------------------

def test_synthesis_multiple_candidate_root_causes():
    """Verify synthesis creates multiple competing candidate causes and identifies secondary factors."""
    synthesis_llm = SynthesisLLMResponse(
        potential_root_causes=[
            PotentialRootCauseItemModel(
                cause_id="PRC-01",
                cause_description="Pneumatic valve actuator elastomeric diaphragm rupture causing coolant failure.",
                cause_category="Machine",
                source_method="Combined",
                supporting_evidence=["Physical tear confirmed during maintenance inspection IR-2026-90"],
                contradictory_evidence=[],
                confidence=0.92,
                rationale="Direct mechanical failure mode substantiated by physical teardown evidence.",
            ),
            PotentialRootCauseItemModel(
                cause_id="PRC-02",
                cause_description="Instrument air supply pressure drop causing actuator spring-to-close.",
                cause_category="Machine",
                source_method="Fishbone",
                supporting_evidence=["Air compressor header showed momentary pressure dip"],
                contradictory_evidence=["Main air reservoir buffer tank check valve held pressure"],
                confidence=0.74,
                rationale="Alternative competing explanation; requires inspection of local air filter regulator.",
                uncertainty_notes="Awaiting data log from air compressor station.",
            ),
        ],
        contributing_factors=[
            ContributingFactorItemModel(
                factor_id="CF-01",
                description="Preventive maintenance interval of 24 months for actuator diaphragms exceeded manufacturer recommendation of 12 months.",
                category="Method",
                related_cause_id="PRC-01",
                supporting_evidence=["Maintenance Schedule SOP-PM-401"],
            )
        ],
    )

    mock_client = _make_mock_client(
        five_whys_resp=FiveWhysLLMResponse(chain=[]),
        fishbone_resp=FishboneLLMResponse(causes=[]),
        evidence_resp=EvidenceAnalysisLLMResponse(items=[]),
        synthesis_resp=synthesis_llm,
    )

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_rca_reasoning_workflow(
            problem_statement="Cooling loss during active exothermic reaction.",
        )

        causes = result.potential_root_causes
        assert len(causes) == 2
        assert causes[0].cause_id == "PRC-01"
        assert causes[0].source_method == "Combined"
        assert causes[1].cause_id == "PRC-02"
        assert causes[1].uncertainty_notes is not None

        factors = result.contributing_factors
        assert len(factors) == 1
        assert factors[0].factor_id == "CF-01"
        assert factors[0].related_cause_id == "PRC-01"


# -----------------------------------------------------------------------------
# 11. SYNTHESIS: HUMAN REVIEW PRESERVATION (GxP GATE)
# -----------------------------------------------------------------------------

def test_synthesis_human_review_preservation_gxp():
    """Verify strict GxP boundary: root causes are never auto-confirmed and human_review_required is True."""
    synthesis_llm = SynthesisLLMResponse(
        potential_root_causes=[
            PotentialRootCauseItemModel(
                cause_id="PRC-01",
                cause_description="Confirmed physical wear of gasket.",
                cause_category="Machine",
                source_method="Five Whys",
                supporting_evidence=["Tear log"],
                contradictory_evidence=[],
                confidence=0.99,
                rationale="High confidence evidence.",
            )
        ],
        contributing_factors=[],
    )

    mock_client = _make_mock_client(
        five_whys_resp=FiveWhysLLMResponse(chain=[]),
        fishbone_resp=FishboneLLMResponse(causes=[]),
        evidence_resp=EvidenceAnalysisLLMResponse(items=[]),
        synthesis_resp=synthesis_llm,
    )

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_rca_reasoning_workflow(
            problem_statement="Gasket wear excursion.",
        )

        # GxP verification gate
        assert result.human_review_required is True
        for cause in result.potential_root_causes:
            # Under no circumstances should an AI output be set to CONFIRMED_ROOT_CAUSE
            assert cause.review_status != CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE
            assert cause.review_status in (
                CauseVerificationStatusEnum.AI_SUGGESTION,
                CauseVerificationStatusEnum.EVIDENCE_SUPPORTED,
            )


# -----------------------------------------------------------------------------
# 12. WORKFLOW ERROR HANDLING & PARTIAL RESULTS
# -----------------------------------------------------------------------------

def test_workflow_error_handling_and_partial_results():
    """Verify that if Groq encounters a timeout, the workflow catches it and preserves partial results."""
    mock_client = MagicMock()
    # Simulate Groq timeout during with_structured_output call
    mock_client.with_structured_output.side_effect = AITimeoutError("Groq request timed out after 30s")

    with patch.object(ai_service, "get_client", return_value=mock_client):
        result = run_rca_reasoning_workflow(
            problem_statement="Sudden pressure drop in distillation vessel.",
        )

        # Workflow must not crash; returns structured fallback with warnings
        assert isinstance(result, RCAWorkflowResult)
        assert len(result.rca_warnings) > 0
        assert any("timed out" in w.lower() for w in result.rca_warnings)
        # Baseline fallback hypotheses were preserved
        assert len(result.five_whys_analysis) > 0
        assert len(result.potential_root_causes) > 0


# -----------------------------------------------------------------------------
# 13. DATABASE PERSISTENCE & HUMAN RECORD PROTECTION
# -----------------------------------------------------------------------------

def test_database_persistence_and_human_record_protection(db):
    """Verify transactional PostgreSQL persistence and non-destruction of human-confirmed causes."""
    suffix = uuid.uuid4().hex[:6].upper()

    # 1. Create real investigation in PostgreSQL
    inv = Investigation(
        investigation_number=f"INV-TEST-{suffix}",
        incident_title="Centrifuge Overheating Excursion",
        incident_description="Centrifuge CF-101 motor bearings exceeded 90 °C temperature threshold.",
        batch_number=f"BATCH-{suffix}",
        equipment="Centrifugation Suite 2",
        investigation_status=InvestigationStatusEnum.OPEN,
        severity=SeverityEnum.HIGH,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    # 2. Add an existing human-confirmed Why and Fishbone cause
    existing_analysis = RCAAnalysis(
        investigation_id=inv.id,
        analysis_method="COMBINED",
        analysis_status="Under Review",
        summary="Initial investigator assessment.",
    )
    db.add(existing_analysis)
    db.flush()

    human_why = FiveWhy(
        rca_analysis_id=existing_analysis.id,
        why_number=1,
        question="Why did centrifuge CF-101 bearing temperature reach 92 °C?",
        answer="Investigator confirmed bearing lubrication oil was degraded with particulates.",
        supporting_evidence_references=["Lubrication Lab Test #LUB-102"],
        is_root_cause=False,
        review_status=CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE,  # Human confirmed!
    )
    existing_analysis.five_whys.append(human_why)

    human_cause = FishboneCauseModel(
        rca_analysis_id=existing_analysis.id,
        category=FishboneCategoryEnum.MANPOWER,
        cause_description="Investigator confirmed shift operator skipped weekly lube oil top-off.",
        evidence_references=["Logbook Entry 2026-10-14"],
        cause_origin="Investigator Added",
        review_status=CauseVerificationStatusEnum.HUMAN_REVIEWED,  # Human reviewed!
    )
    existing_analysis.fishbone_causes.append(human_cause)
    db.commit()

    # 3. Generate AI RCA workflow result with AI suggestions
    rca_res = RCAWorkflowResult(
        workflow_id=f"WF-RCA-{suffix}",
        investigation_id=str(inv.id),
        problem_statement="Centrifuge CF-101 motor bearings exceeded 90 °C.",
        five_whys_analysis=[
            # Level 1 will be ignored because human_why exists at level 1
            FiveWhysLevel(
                level=1,
                question="Why did bearings overheat?",
                answer="AI guess at level 1",
                is_root_cause=False,
                status=CauseVerificationStatusEnum.AI_SUGGESTION,
            ),
            # Level 2 will be added
            FiveWhysLevel(
                level=2,
                question="Why was lubrication oil degraded?",
                answer="Severe thermal oxidation due to prolonged operation above rated speed.",
                is_root_cause=True,
                status=CauseVerificationStatusEnum.AI_SUGGESTION,
            ),
        ],
        fishbone_analysis=[
            FishboneCause(
                cause_id="CAUSE-AI-01",
                category=FishboneCategoryEnum.MACHINE,
                cause_description="Bearing race pitting from mechanical fatigue.",
                supporting_evidence_references=["Vibration analysis"],
                confidence=0.85,
            )
        ],
        evidence_assessment=[
            EvidenceAssessment(
                evidence_id="EVD-AI-01",
                evidence_description=f"Bearing vibration spike documented on CF-101 {suffix}",
                evidence_type=EvidenceTypeEnum.SUPPORTING,
                source_reference="SCADA Vibration Trend",
            )
        ],
        potential_root_causes=[],
        contributing_factors=[],
    )

    # 4. Persist result
    persisted = rca_service.persist_rca_workflow_result(
        db=db,
        investigation_id=str(inv.id),
        rca_result=rca_res,
    )

    assert persisted is not None
    db.refresh(persisted)

    # 5. Verify human records were preserved!
    why_levels = {w.why_number: w for w in persisted.five_whys}
    assert 1 in why_levels
    # Level 1 must still be the human confirmed why!
    assert why_levels[1].review_status == CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE
    assert "Investigator confirmed bearing lubrication oil was degraded" in why_levels[1].answer

    # Level 2 is the new AI why
    assert 2 in why_levels
    assert why_levels[2].review_status == CauseVerificationStatusEnum.AI_SUGGESTION

    # Fishbone: Human reviewed cause is retained, AI cause is added
    categories = [c.category for c in persisted.fishbone_causes]
    assert FishboneCategoryEnum.MANPOWER in categories
    manpower_cause = next(c for c in persisted.fishbone_causes if c.category == FishboneCategoryEnum.MANPOWER)
    assert manpower_cause.review_status == CauseVerificationStatusEnum.HUMAN_REVIEWED

    machine_cause = next(c for c in persisted.fishbone_causes if c.category == FishboneCategoryEnum.MACHINE)
    assert machine_cause.cause_origin == "AI Suggestion"


# -----------------------------------------------------------------------------
# 14. API ENDPOINT: POST /api/investigations/{id}/rca/generate
# -----------------------------------------------------------------------------

def test_api_generate_rca_endpoint(db):
    """Verify that POST /api/investigations/{id}/rca/generate invokes RCA reasoning and returns 200."""
    suffix = uuid.uuid4().hex[:6].upper()

    # Create investigation
    inv = Investigation(
        investigation_number=f"INV-API-{suffix}",
        incident_title="Column Pressure Excursion",
        incident_description="Distillation column DC-401 experienced differential pressure collapse.",
        batch_number=f"BATCH-API-{suffix}",
        equipment="Distillation Unit D",
        investigation_status=InvestigationStatusEnum.OPEN,
        severity=SeverityEnum.MEDIUM,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    whys_llm = FiveWhysLLMResponse(
        chain=[
            FiveWhysItemModel(
                level=1,
                question="Why did column pressure collapse?",
                answer="Condenser cooling water flow surged excessively.",
                is_root_cause=True,
            )
        ]
    )

    mock_client = _make_mock_client(
        five_whys_resp=whys_llm,
        fishbone_resp=FishboneLLMResponse(causes=[]),
        evidence_resp=EvidenceAnalysisLLMResponse(items=[]),
        synthesis_resp=SynthesisLLMResponse(potential_root_causes=[], contributing_factors=[]),
    )

    with patch.object(ai_service, "get_client", return_value=mock_client):
        response = client.post(
            f"/api/investigations/{inv.id}/rca/generate",
            json={
                "problem_statement": "Column differential pressure collapse.",
                "persist": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"].startswith("WF-RCA")
        assert data["problem_statement"] == "Column differential pressure collapse."
        assert len(data["five_whys_analysis"]) == 1
        assert data["five_whys_analysis"][0]["is_root_cause"] is True
        assert data["human_review_required"] is True
        assert data["persisted_in_db"] is True
        assert data["analysis_id"] is not None


def test_api_generate_rca_nonexistent_investigation():
    """Verify that generating RCA for a non-existent investigation returns 404."""
    random_id = str(uuid.uuid4())
    response = client.post(
        f"/api/investigations/{random_id}/rca/generate",
        json={"persist": False},
    )
    assert response.status_code == 404
    err_body = response.json()
    err_text = err_body.get("detail", err_body.get("message", ""))
    assert f"Investigation '{random_id}' not found" in err_text
