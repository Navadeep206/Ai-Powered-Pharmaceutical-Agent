"""Finalization node for LangGraph incident extraction workflow.

Assembles the final validated ExtractionAnalysisResponse, records duration metrics,
preserves warnings and failure diagnostics, and marks workflow completion.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.agents.state import ExtractionWorkflowState
from app.core.logging import get_logger
from app.schemas.document import IntakeMethodEnum
from app.schemas.extraction import (
    ExtractionAnalysisResponse,
    IncidentExtractedData,
    OverallExtractionStatus,
)
from app.services.extraction_service import extraction_service

logger = get_logger("agents.nodes.finalization")


def finalization_node(state: ExtractionWorkflowState) -> Dict[str, Any]:
    """Consolidate workflow results and assemble final reviewable extraction response."""
    workflow_id = state.get("workflow_id", "WF-EXTRACT")
    logger.info("Executing FinalizationNode for workflow %s", workflow_id)

    # 1. Calculate duration
    completed_at = datetime.now(timezone.utc)
    started_at_str = state.get("processing_started_at")
    duration_seconds: float = 0.0

    if started_at_str:
        try:
            started_at = datetime.fromisoformat(started_at_str)
            duration_seconds = round((completed_at - started_at).total_seconds(), 3)
        except Exception:
            duration_seconds = 0.0

    # 2. Determine final workflow status
    is_failed = state.get("workflow_status") == "FAILED"
    final_workflow_status = "FAILED" if is_failed else "COMPLETED"

    # 3. Retrieve or build extraction artifacts
    extracted_data = state.get("extracted_data")
    source_type_str = state.get("source_type") or "Text"

    # Map source type to IntakeMethodEnum
    try:
        intake_method = IntakeMethodEnum(source_type_str)
    except Exception:
        intake_method = IntakeMethodEnum.TEXT

    if extracted_data is None:
        extracted_data = extraction_service._create_empty_extracted_data(source_type=source_type_str)

    raw_ext_status = state.get("extraction_status") or (
        OverallExtractionStatus.FAILED.value if is_failed else OverallExtractionStatus.NEEDS_REVIEW.value
    )
    try:
        final_ext_status = OverallExtractionStatus(raw_ext_status)
    except Exception:
        final_ext_status = OverallExtractionStatus.FAILED if is_failed else OverallExtractionStatus.NEEDS_REVIEW

    warnings = list(state.get("warnings") or [])
    if is_failed and state.get("error_message"):
        if state["error_message"] not in warnings:
            warnings.append(state["error_message"])

    # Collect fields requiring review
    fields_requiring_review: List[str] = list(state.get("ambiguous_fields") or [])
    field_names = [
        "incident_title", "incident_description", "deviation_id", "batch_number",
        "product_name", "api_name", "department", "equipment_id", "process_stage",
        "incident_date", "detection_date", "expected_condition", "actual_condition",
        "immediate_action_taken", "potential_impact", "observations", "detection_method",
        "personnel_roles_involved", "relevant_measurements", "relevant_operating_parameters"
    ]
    for fn in field_names:
        f_obj = getattr(extracted_data, fn, None)
        if f_obj and f_obj.requires_human_review and fn not in fields_requiring_review:
            fields_requiring_review.append(fn)

    # Summary narrative
    completeness = state.get("completeness_score", 0.0)
    if is_failed:
        summary = f"Workflow execution failed: {state.get('error_message', 'Unknown processing error')}."
    elif final_ext_status == OverallExtractionStatus.OCR_REQUIRED:
        summary = "No extractable text was found in the uploaded document. Please perform OCR preprocessing before submitting for AI analysis."
    elif final_ext_status == OverallExtractionStatus.COMPLETED:
        summary = f"Incident information extracted successfully with {completeness}% document coverage."
    elif final_ext_status == OverallExtractionStatus.PARTIALLY_COMPLETED:
        summary = f"Partial extraction completed ({completeness}% document coverage). Review required for missing fields."
    else:
        summary = f"Extraction completed ({completeness}% coverage). Investigator review required for discrepancies."

    # Assemble response contract
    final_response = ExtractionAnalysisResponse(
        analysis_id=workflow_id,
        workflow_id=workflow_id,
        workflow_status=final_workflow_status,
        duration_seconds=duration_seconds,
        intake_method=intake_method,
        extraction_status=final_ext_status,
        extracted_data=extracted_data,
        missing_fields=list(state.get("missing_fields") or []),
        critical_gaps=list(state.get("critical_gaps") or []),
        ambiguous_fields=list(state.get("ambiguous_fields") or []),
        possible_contradictions=list(state.get("possible_contradictions") or []),
        investigator_questions=list(state.get("investigator_questions") or []),
        completeness_score=completeness,
        extraction_warnings=warnings,
        warnings=warnings,
        fields_requiring_review=fields_requiring_review,
        extraction_summary=summary,
        overall_confidence=state.get("overall_confidence", 0.0),
    )

    logger.info(
        "Workflow %s finalized: workflow_status=%s, extraction_status=%s, duration=%.3fs",
        workflow_id,
        final_workflow_status,
        final_ext_status.value,
        duration_seconds,
    )

    return {
        "workflow_status": final_workflow_status,
        "processing_completed_at": completed_at.isoformat(),
        "duration_seconds": duration_seconds,
        "warnings": warnings,
        "extraction_response": final_response,
    }
