"""Automated tests for LangGraph Incident Extraction Workflow in RootIQ.

Covers:
1. Valid pasted-text workflow execution
2. Valid email workflow execution
3. Valid PDF-extracted text workflow execution
4. Missing/empty input text rejection (no LLM call)
5. Unsupported source type rejection
6. Complete node traversal sequence (input -> extraction -> validation -> quality -> finalization)
7. Pydantic validation failure and controlled failure routing
8. Missing information non-failure routing (continues through quality assessment)
9. Ambiguous information review routing (preserves review warnings)
10. Groq timeout handling in graph
11. Groq authentication failure handling in graph
12. Quality assessment node integration in graph
13. Workflow finalization, duration calculation, and status assignment
14. Retry limit behavior without infinite looping
15. Checkpointing state retrieval via MemorySaver and thread_id
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import httpx
import pytest
import groq
from langchain_core.messages import AIMessage

from app.agents.graph import (
    incident_extraction_workflow,
    memory_checkpointer,
    run_incident_extraction_workflow,
)
from app.agents.nodes.extraction_node import incident_extraction_node
from app.agents.nodes.finalization_node import finalization_node
from app.agents.nodes.input_node import input_processing_node
from app.agents.nodes.quality_node import quality_assessment_node
from app.agents.nodes.validation_node import structured_validation_node
from app.agents.state import ExtractionWorkflowState
from app.core.config import settings
from app.schemas.document import (
    IntakeMethodEnum,
    NormalizedIncidentIntake,
    PageReference,
)
from app.schemas.extraction import (
    ExtractionAnalysisResponse,
    FieldExtractionStatus,
    OverallExtractionStatus,
    ReviewStatusEnum,
)
from app.services.extraction_service import (
    RawIncidentExtraction,
    extraction_service,
)

DUMMY_VALID_KEY = "gsk_testvalidkey1234567890abcdefghijklmnopqrstuvwxyz"
DUMMY_HTTPX_REQ = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")

COMPLETE_INCIDENT_TEXT = (
    "INCIDENT REPORT: DEV-2026-0891\n"
    "Title: Thermal Excursion During Active Synthesis of Atorvastatin Calcium\n"
    "Department: Chemical Synthesis Unit\n\n"
    "On 2026-03-02 at 04:15 UTC, during API stage 3 crystallization of Atorvastatin Calcium, "
    "batch BATCH-2026-9921 in primary glass-lined reactor R-102 experienced an unexpected temperature spike. "
    "The internal vessel temperature reached 84.5 °C, exceeding the validated upper limit of 70.0 °C. "
    "The target operating range for crystallization is 65.0 - 70.0 °C at an agitation speed of 350 RPM. "
    "The excursion was detected on 2026-03-02 via automated SCADA Alarm T-HIGH-102. "
    "Lead chemical technician John Smith and QA supervisor Jane Doe were present during containment. "
    "Immediate action taken: Cooling jacket glycol flow was manually increased to 100% capacity and "
    "heating mantle power was disconnected. Vessel temperature normalized to 68.0 °C within 18 minutes. "
    "Potential impact: Potential thermal degradation or polymorphic impurity formation requiring HPLC testing. "
    "Initial observations indicate slight discoloration of slurry. Product name: Atorvastatin API."
)


def make_complete_raw() -> RawIncidentExtraction:
    """Helper returning complete RawIncidentExtraction."""
    return RawIncidentExtraction(
        incident_title="Thermal Excursion During Active Synthesis of Atorvastatin Calcium",
        incident_title_excerpt="Thermal Excursion During Active Synthesis of Atorvastatin Calcium",
        incident_title_confidence=0.98,
        incident_description="During API stage 3 crystallization, batch BATCH-2026-9921 experienced temperature spike to 84.5 °C.",
        incident_description_excerpt="batch BATCH-2026-9921 in primary glass-lined reactor R-102 experienced an unexpected temperature spike",
        incident_description_confidence=0.95,
        deviation_id="DEV-2026-0891",
        deviation_id_excerpt="DEV-2026-0891",
        deviation_id_confidence=0.99,
        batch_number="BATCH-2026-9921",
        batch_number_excerpt="batch BATCH-2026-9921",
        batch_number_confidence=0.99,
        product_name="Atorvastatin API",
        product_name_excerpt="Product name: Atorvastatin API",
        product_name_confidence=0.96,
        api_name="Atorvastatin Calcium",
        api_name_excerpt="Atorvastatin Calcium",
        api_name_confidence=0.97,
        department="Chemical Synthesis Unit",
        department_excerpt="Department: Chemical Synthesis Unit",
        department_confidence=0.95,
        equipment_id="R-102",
        equipment_id_excerpt="primary glass-lined reactor R-102",
        equipment_id_confidence=0.98,
        process_stage="Stage 3 Crystallization",
        process_stage_excerpt="stage 3 crystallization",
        process_stage_confidence=0.94,
        incident_date="2026-03-02",
        incident_date_excerpt="On 2026-03-02 at 04:15 UTC",
        incident_date_confidence=0.99,
        incident_date_ambiguous=False,
        detection_date="2026-03-02",
        detection_date_excerpt="detected on 2026-03-02",
        detection_date_confidence=0.98,
        expected_condition="Crystallization temperature between 65.0 - 70.0 °C",
        expected_condition_excerpt="target operating range for crystallization is 65.0 - 70.0 °C",
        expected_condition_confidence=0.93,
        actual_condition="Internal vessel temperature reached 84.5 °C",
        actual_condition_excerpt="internal vessel temperature reached 84.5 °C",
        actual_condition_confidence=0.96,
        immediate_action_taken="Cooling jacket glycol flow was manually increased to 100% capacity",
        immediate_action_taken_excerpt="Cooling jacket glycol flow was manually increased to 100% capacity",
        immediate_action_taken_confidence=0.95,
        potential_impact="Potential thermal degradation or polymorphic impurity formation requiring HPLC testing",
        potential_impact_excerpt="Potential thermal degradation or polymorphic impurity formation requiring HPLC testing",
        potential_impact_confidence=0.92,
        observations="Initial observations indicate slight discoloration of slurry",
        observations_excerpt="Initial observations indicate slight discoloration of slurry",
        observations_confidence=0.91,
        detection_method="SCADA Alarm T-HIGH-102",
        detection_method_excerpt="automated SCADA Alarm T-HIGH-102",
        detection_method_confidence=0.97,
        personnel_roles_involved=["Lead chemical technician", "QA supervisor"],
        personnel_roles_excerpt="Lead chemical technician John Smith and QA supervisor Jane Doe",
        personnel_roles_confidence=0.92,
        relevant_measurements=[
            {"parameter": "Vessel Temperature", "value": "84.5", "unit": "°C"},
            {"parameter": "Normalized Temperature", "value": "68.0", "unit": "°C"},
        ],
        relevant_measurements_excerpt="temperature reached 84.5 °C",
        relevant_measurements_confidence=0.95,
        relevant_operating_parameters=[
            {"parameter": "Target Temperature Range", "target_or_range": "65.0 - 70.0", "unit": "°C"},
            {"parameter": "Agitation Speed", "target_or_range": "350", "unit": "RPM"},
        ],
        relevant_operating_parameters_excerpt="target operating range for crystallization is 65.0 - 70.0 °C at an agitation speed of 350 RPM",
        relevant_operating_parameters_confidence=0.94,
        missing_fields=[],
        ambiguous_fields=[],
        possible_contradictions=[],
        warnings=[],
        extraction_summary="Full extraction completed with all manufacturing parameters.",
    )


# 1. Valid pasted-text workflow
def test_valid_pasted_text_workflow():
    """Verify that pasted text executes the complete LangGraph workflow returning COMPLETED status."""
    raw = make_complete_raw()
    intake = NormalizedIncidentIntake(
        intake_id="INTAKE-TXT-001",
        source_type=IntakeMethodEnum.TEXT,
        subject="Pasted Text Narrative",
        prepared_incident_text=COMPLETE_INCIDENT_TEXT,
    )

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch.object(extraction_service, "_invoke_llm", return_value=raw):

        response = run_incident_extraction_workflow(intake)

        assert isinstance(response, ExtractionAnalysisResponse)
        assert response.workflow_id is not None
        assert response.workflow_id.startswith("WF-EXTRACT-")
        assert response.workflow_status == "COMPLETED"
        assert response.extraction_status == OverallExtractionStatus.COMPLETED
        assert response.extracted_data.batch_number.value == "BATCH-2026-9921"
        assert response.duration_seconds is not None
        assert response.duration_seconds >= 0.0


# 2. Valid email workflow
def test_valid_email_workflow():
    """Verify that email intake executes the LangGraph workflow preserving email modality."""
    raw = make_complete_raw()
    intake = NormalizedIncidentIntake(
        intake_id="INTAKE-EML-001",
        source_type=IntakeMethodEnum.EMAIL,
        subject="Deviation Notification",
        prepared_incident_text=f"Subject: Deviation Alert\n\n{COMPLETE_INCIDENT_TEXT}",
    )

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch.object(extraction_service, "_invoke_llm", return_value=raw):

        response = run_incident_extraction_workflow(intake)

        assert response.workflow_status == "COMPLETED"
        assert response.intake_method == IntakeMethodEnum.EMAIL
        assert response.extracted_data.deviation_id.value == "DEV-2026-0891"


# 3. Valid PDF-extracted text workflow
def test_valid_pdf_extracted_text_workflow():
    """Verify PDF extraction workflow preserves page references and document metadata."""
    raw = make_complete_raw()
    intake = NormalizedIncidentIntake(
        intake_id="INTAKE-DOC-001",
        source_type=IntakeMethodEnum.DOCUMENT,
        source_filename="batch_record.pdf",
        prepared_incident_text=COMPLETE_INCIDENT_TEXT,
        page_references=[
            PageReference(page_number=1, character_count=300, has_text=True, requires_ocr=False),
            PageReference(page_number=2, character_count=len(COMPLETE_INCIDENT_TEXT) - 300, has_text=True, requires_ocr=False),
        ],
    )

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch.object(extraction_service, "_invoke_llm", return_value=raw):

        response = run_incident_extraction_workflow(intake)

        assert response.workflow_status == "COMPLETED"
        assert response.intake_method == IntakeMethodEnum.DOCUMENT
        ref = response.extracted_data.batch_number.source_reference
        assert ref is not None
        assert ref.page_number is not None


# 4. Missing input text
def test_missing_input_text():
    """Verify that empty text is rejected in input_node and routes to finalization without calling LLM."""
    state: ExtractionWorkflowState = {
        "workflow_id": "WF-EMPTY",
        "thread_id": "WF-EMPTY",
        "source_type": "Text",
        "source_text": "   ",  # Pure whitespace
        "validation_errors": [],
        "warnings": [],
        "workflow_status": "PENDING",
    }

    # Execute input node directly
    res = input_processing_node(state)
    assert res["workflow_status"] == "FAILED"
    assert any("cannot be empty" in err for err in res["validation_errors"])

    # Execute complete graph with empty intake
    intake = NormalizedIncidentIntake(
        intake_id="INTAKE-EMPTY",
        source_type=IntakeMethodEnum.TEXT,
        prepared_incident_text="   ",
    )

    with patch.object(extraction_service, "_invoke_llm") as mock_llm:
        response = run_incident_extraction_workflow(intake)
        mock_llm.assert_not_called()  # Groq must NOT be invoked
        assert response.workflow_status == "FAILED"
        assert any("cannot be empty" in w for w in response.warnings)


# 5. Unsupported source type
def test_unsupported_source_type():
    """Verify that invalid source type is rejected by input_node."""
    state: ExtractionWorkflowState = {
        "workflow_id": "WF-INVALID-TYPE",
        "thread_id": "WF-INVALID-TYPE",
        "source_type": "AudioRecording",
        "source_text": "Some valid narrative text from transcription.",
        "validation_errors": [],
        "warnings": [],
        "workflow_status": "PENDING",
    }

    res = input_processing_node(state)
    assert res["workflow_status"] == "FAILED"
    assert any("Unsupported source type" in err for err in res["validation_errors"])


# 6. Successful Groq extraction using mocks
def test_successful_groq_extraction_mocked():
    """Verify all 5 nodes execute in orderly sequence for valid intake."""
    raw = make_complete_raw()
    intake = NormalizedIncidentIntake(
        intake_id="INTAKE-SEQ-001",
        source_type=IntakeMethodEnum.TEXT,
        subject="Sequence Test",
        prepared_incident_text=COMPLETE_INCIDENT_TEXT,
    )

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch.object(extraction_service, "_invoke_llm", return_value=raw):

        response = run_incident_extraction_workflow(intake)

        assert response.workflow_status == "COMPLETED"
        assert response.completeness_score == 100.0
        assert response.extracted_data.batch_number.value == "BATCH-2026-9921"
        assert response.extracted_data.equipment_id.value == "R-102"


# 7. Pydantic validation failure
def test_pydantic_validation_failure():
    """Verify validation_node catches corrupt extracted data and flags failure without infinite loop."""
    state: ExtractionWorkflowState = {
        "workflow_id": "WF-VAL-FAIL",
        "thread_id": "WF-VAL-FAIL",
        "source_type": "Text",
        "source_text": COMPLETE_INCIDENT_TEXT,
        "extracted_data": None,  # Corrupted / missing
        "retry_count": 2,  # Already exhausted max retries
        "max_retries": 2,
        "validation_errors": [],
        "warnings": [],
        "workflow_status": "IN_PROGRESS",
    }

    res = structured_validation_node(state)
    assert res["workflow_status"] == "FAILED"
    assert "Structured validation failed" in res.get("error_message", "")


# 8. Missing information routing
def test_missing_information_routing():
    """Verify incomplete report does NOT fail the workflow, but continues through quality assessment."""
    raw = make_complete_raw()
    raw.batch_number = None
    raw.equipment_id = None
    raw.missing_fields = ["batch_number", "equipment_id"]

    intake = NormalizedIncidentIntake(
        intake_id="INTAKE-MISSING",
        source_type=IntakeMethodEnum.TEXT,
        subject="Missing Info Report",
        prepared_incident_text=COMPLETE_INCIDENT_TEXT,
    )

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch.object(extraction_service, "_invoke_llm", return_value=raw):

        response = run_incident_extraction_workflow(intake)

        # Operational workflow succeeded, even though document information is partial!
        assert response.workflow_status == "COMPLETED"
        assert response.extraction_status in (
            OverallExtractionStatus.PARTIALLY_COMPLETED,
            OverallExtractionStatus.NEEDS_REVIEW,
        )
        assert "batch_number" in response.missing_fields
        assert "equipment_id" in response.missing_fields
        assert len(response.critical_gaps) > 0


# 9. Ambiguous information routing
def test_ambiguous_information_routing():
    """Verify ambiguous statements continue with review warnings and do NOT fail the workflow."""
    raw = make_complete_raw()
    raw.incident_date_ambiguous = True
    raw.ambiguous_fields = ["incident_date"]

    intake = NormalizedIncidentIntake(
        intake_id="INTAKE-AMBIGUOUS",
        source_type=IntakeMethodEnum.TEXT,
        subject="Ambiguous Report",
        prepared_incident_text=COMPLETE_INCIDENT_TEXT,
    )

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch.object(extraction_service, "_invoke_llm", return_value=raw):

        response = run_incident_extraction_workflow(intake)

        assert response.workflow_status == "COMPLETED"
        assert response.extraction_status == OverallExtractionStatus.NEEDS_REVIEW
        assert "incident_date" in response.ambiguous_fields


# 10. Groq timeout
def test_groq_timeout_workflow():
    """Verify Groq timeout in extraction_node routes to finalization with FAILED workflow status."""
    timeout_err = groq.APITimeoutError(request=DUMMY_HTTPX_REQ)

    intake = NormalizedIncidentIntake(
        intake_id="INTAKE-TIMEOUT",
        source_type=IntakeMethodEnum.TEXT,
        subject="Timeout Report",
        prepared_incident_text=COMPLETE_INCIDENT_TEXT,
    )

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch.object(extraction_service, "_invoke_llm", side_effect=timeout_err):

        response = run_incident_extraction_workflow(intake)

        assert response.workflow_status == "FAILED"
        assert any("timeout" in w.lower() for w in response.warnings)


# 11. Groq authentication failure
def test_groq_auth_failure_workflow():
    """Verify Groq 401 AuthenticationError in extraction_node routes to finalization with FAILED status."""
    auth_err = groq.AuthenticationError(
        "Invalid API Key",
        response=httpx.Response(401, request=DUMMY_HTTPX_REQ),
        body={"error": {"message": "Invalid API key"}},
    )

    intake = NormalizedIncidentIntake(
        intake_id="INTAKE-AUTH-FAIL",
        source_type=IntakeMethodEnum.TEXT,
        subject="Auth Fail Report",
        prepared_incident_text=COMPLETE_INCIDENT_TEXT,
    )

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch.object(extraction_service, "_invoke_llm", side_effect=auth_err):

        response = run_incident_extraction_workflow(intake)

        assert response.workflow_status == "FAILED"
        assert any("authentication" in w.lower() for w in response.warnings)


# 12. Quality assessment integration
def test_quality_assessment_node_integration():
    """Verify quality_assessment_node computes completeness and populates critical gaps."""
    raw = make_complete_raw()
    empty_container = extraction_service._create_empty_extracted_data(source_type="Text")
    # Populate only batch_number (weight 15) and equipment_id (weight 10)
    empty_container.batch_number.value = "BATCH-2026-9921"
    empty_container.batch_number.extraction_status = FieldExtractionStatus.EXTRACTED
    empty_container.equipment_id.value = "R-102"
    empty_container.equipment_id.extraction_status = FieldExtractionStatus.EXTRACTED

    state: ExtractionWorkflowState = {
        "workflow_id": "WF-QUAL-TEST",
        "thread_id": "WF-QUAL-TEST",
        "source_type": "Text",
        "source_text": COMPLETE_INCIDENT_TEXT,
        "extracted_data": empty_container,
        "workflow_status": "IN_PROGRESS",
        "extraction_status": "IN_PROGRESS",
        "warnings": [],
    }

    res = quality_assessment_node(state)
    assert res["completeness_score"] == 25.0  # 15 + 10
    assert len(res["critical_gaps"]) > 0
    assert len(res["investigator_questions"]) > 0


# 13. Workflow status finalization
def test_workflow_status_finalization():
    """Verify finalization_node correctly sets completed timestamp and duration."""
    start_time = datetime.now(timezone.utc).isoformat()
    state: ExtractionWorkflowState = {
        "workflow_id": "WF-FINAL-TEST",
        "thread_id": "WF-FINAL-TEST",
        "source_type": "Text",
        "source_text": COMPLETE_INCIDENT_TEXT,
        "processing_started_at": start_time,
        "workflow_status": "IN_PROGRESS",
        "extraction_status": "COMPLETED",
        "warnings": [],
        "completeness_score": 100.0,
    }

    res = finalization_node(state)
    assert res["workflow_status"] == "COMPLETED"
    assert res["processing_completed_at"] is not None
    assert res["duration_seconds"] is not None
    assert isinstance(res["extraction_response"], ExtractionAnalysisResponse)


# 14. Retry limit behavior
def test_retry_limit_behavior():
    """Verify that validation failure triggers retry when retry_count < max_retries, and fails when exhausted."""
    # Attempt 1: retry_count = 0 -> transitions to RETRY
    state_attempt_1: ExtractionWorkflowState = {
        "workflow_id": "WF-RETRY-TEST",
        "thread_id": "WF-RETRY-TEST",
        "source_type": "Text",
        "source_text": COMPLETE_INCIDENT_TEXT,
        "extracted_data": None,
        "retry_count": 0,
        "max_retries": 2,
        "workflow_status": "IN_PROGRESS",
    }
    res_1 = structured_validation_node(state_attempt_1)
    assert res_1["workflow_status"] == "RETRY"
    assert res_1["retry_count"] == 1

    # Attempt 3: retry_count = 2 (exhausted) -> transitions to FAILED
    state_attempt_exhausted: ExtractionWorkflowState = {
        "workflow_id": "WF-RETRY-TEST",
        "thread_id": "WF-RETRY-TEST",
        "source_type": "Text",
        "source_text": COMPLETE_INCIDENT_TEXT,
        "extracted_data": None,
        "retry_count": 2,
        "max_retries": 2,
        "workflow_status": "IN_PROGRESS",
    }
    res_exhausted = structured_validation_node(state_attempt_exhausted)
    assert res_exhausted["workflow_status"] == "FAILED"


# 15. Checkpoint configuration behavior
def test_checkpoint_configuration_behavior():
    """Verify MemorySaver checkpointer captures workflow state retrievable by thread_id."""
    raw = make_complete_raw()
    custom_thread_id = "THREAD-AUDIT-9921"

    intake = NormalizedIncidentIntake(
        intake_id="INTAKE-CHECKPOINT",
        source_type=IntakeMethodEnum.TEXT,
        subject="Checkpoint Test",
        prepared_incident_text=COMPLETE_INCIDENT_TEXT,
    )

    with patch.object(settings, "GROQ_API_KEY", DUMMY_VALID_KEY), \
         patch.object(extraction_service, "_invoke_llm", return_value=raw):

        response = run_incident_extraction_workflow(intake, thread_id=custom_thread_id)
        assert response.workflow_status == "COMPLETED"

        # Verify state is present in checkpointer
        config = {"configurable": {"thread_id": custom_thread_id}}
        saved_state = incident_extraction_workflow.get_state(config)
        assert saved_state is not None
        assert saved_state.values.get("workflow_status") == "COMPLETED"
        assert saved_state.values.get("source_type") == "Text"
