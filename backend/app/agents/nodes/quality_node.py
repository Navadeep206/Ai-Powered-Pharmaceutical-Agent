"""Quality assessment node for LangGraph incident extraction workflow.

Invokes the existing ExtractionQualityService to evaluate GxP completeness coverage,
identify critical missing attributes, detect contradictions, and generate targeted inquiries.
"""

from typing import Any, Dict, List
from app.agents.state import ExtractionWorkflowState
from app.core.logging import get_logger
from app.schemas.extraction import OverallExtractionStatus
from app.services.extraction_quality_service import extraction_quality_service

logger = get_logger("agents.nodes.quality")


def quality_assessment_node(state: ExtractionWorkflowState) -> Dict[str, Any]:
    """Execute GxP completeness assessment and contradiction detection."""
    logger.info("Executing QualityAssessmentNode for workflow %s", state.get("workflow_id"))

    # Skip if prior node flagged failure
    if state.get("workflow_status") == "FAILED":
        return {}

    extracted_data = state.get("extracted_data")
    source_text = state.get("source_text") or ""
    current_status = state.get("extraction_status")
    warnings = list(state.get("warnings") or [])

    # If already marked OCR_REQUIRED or FAILED, preserve without overwriting
    if current_status in (OverallExtractionStatus.OCR_REQUIRED.value, OverallExtractionStatus.FAILED.value):
        return {}

    if not extracted_data:
        logger.warning("Quality assessment called without extracted data container.")
        return {
            "completeness_score": 0.0,
            "missing_fields": [],
            "critical_gaps": [],
            "ambiguous_fields": [],
            "possible_contradictions": [],
            "investigator_questions": [],
        }

    # 1. Evaluate Completeness and Critical Evidence Gaps
    quality_res = extraction_quality_service.assess_completeness_and_gaps(extracted_data)
    completeness_score = quality_res["completeness_score"]
    missing_fields = quality_res["missing_fields"]
    critical_gaps = quality_res["critical_gaps"]
    investigator_questions = quality_res["investigator_questions"]

    # 2. Detect Contradictions and Inconsistencies
    contradictions = extraction_quality_service.detect_contradictions(
        extracted_data=extracted_data,
        source_text=source_text,
    )

    ambiguous_fields = list(state.get("ambiguous_fields") or [])
    for c in contradictions:
        if c.field_name not in ambiguous_fields:
            ambiguous_fields.append(c.field_name)
        c_warn = f"Contradiction identified in {c.field_name}: {c.description}"
        if c_warn not in warnings:
            warnings.append(c_warn)

    # 3. Determine Overall Extraction Status
    overall_conf = state.get("overall_confidence", 0.0)
    if len(contradictions) > 0 or len(ambiguous_fields) > 0 or overall_conf < 0.60:
        new_extraction_status = OverallExtractionStatus.NEEDS_REVIEW.value
    elif len(missing_fields) > 0:
        new_extraction_status = OverallExtractionStatus.PARTIALLY_COMPLETED.value
    else:
        new_extraction_status = OverallExtractionStatus.COMPLETED.value

    logger.info(
        "Quality assessment finished: completeness=%.1f%%, gaps=%d, contradictions=%d, status=%s",
        completeness_score,
        len(critical_gaps),
        len(contradictions),
        new_extraction_status,
    )

    return {
        "completeness_score": completeness_score,
        "missing_fields": missing_fields,
        "critical_gaps": critical_gaps,
        "ambiguous_fields": ambiguous_fields,
        "possible_contradictions": contradictions,
        "investigator_questions": investigator_questions,
        "extraction_status": new_extraction_status,
        "warnings": warnings,
    }
