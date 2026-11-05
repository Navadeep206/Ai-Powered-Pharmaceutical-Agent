"""Structured validation node for LangGraph incident extraction workflow.

Validates extracted attributes against Pydantic schemas, verifies confidence bounds,
checks source reference character offsets, and manages controlled retry routing.
"""

from typing import Any, Dict, List
from pydantic import ValidationError

from app.agents.state import ExtractionWorkflowState
from app.core.logging import get_logger
from app.schemas.extraction import (
    ExtractedField,
    IncidentExtractedData,
)
from app.services.extraction_quality_service import extraction_quality_service

logger = get_logger("agents.nodes.validation")


def structured_validation_node(state: ExtractionWorkflowState) -> Dict[str, Any]:
    """Audit field structures, confidence bounds, and provenance without silently guessing."""
    logger.info("Executing StructuredValidationNode for workflow %s", state.get("workflow_id"))

    # Skip if prior node failed
    if state.get("workflow_status") == "FAILED":
        return {}

    extracted_data = state.get("extracted_data")
    source_text = state.get("source_text") or ""
    validation_errors = list(state.get("validation_errors") or [])
    warnings = list(state.get("warnings") or [])
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    # 1. Verify extracted_data presence
    if extracted_data is None:
        err_msg = "Extracted data container is missing from workflow state."
        logger.error(err_msg)
        validation_errors.append(err_msg)

        if retry_count < max_retries:
            logger.info("Scheduling controlled validation retry (%d/%d)", retry_count + 1, max_retries)
            return {
                "retry_count": retry_count + 1,
                "workflow_status": "RETRY",
                "validation_errors": validation_errors,
            }
        else:
            return {
                "workflow_status": "FAILED",
                "error_message": "Structured validation failed: no extraction artifacts produced after retries.",
                "validation_errors": validation_errors,
            }

    # 2. Validate extracted_data conforms to IncidentExtractedData schema
    if not isinstance(extracted_data, IncidentExtractedData):
        try:
            if isinstance(extracted_data, dict):
                extracted_data = IncidentExtractedData(**extracted_data)
            else:
                raise TypeError(f"Expected IncidentExtractedData, got {type(extracted_data)}")
        except (ValidationError, TypeError) as val_err:
            err_msg = f"Extracted data schema validation failure: {val_err}"
            logger.error(err_msg)
            validation_errors.append(err_msg)

            if retry_count < max_retries:
                logger.info("Scheduling controlled validation retry (%d/%d)", retry_count + 1, max_retries)
                return {
                    "retry_count": retry_count + 1,
                    "workflow_status": "RETRY",
                    "validation_errors": validation_errors,
                }
            else:
                return {
                    "workflow_status": "FAILED",
                    "error_message": err_msg,
                    "validation_errors": validation_errors,
                }

    # 3. Audit confidence scores & source reference offsets across fields
    field_names = [
        "incident_title", "incident_description", "deviation_id", "batch_number",
        "product_name", "api_name", "department", "equipment_id", "process_stage",
        "incident_date", "detection_date", "expected_condition", "actual_condition",
        "immediate_action_taken", "potential_impact", "observations", "detection_method",
        "personnel_roles_involved", "relevant_measurements", "relevant_operating_parameters"
    ]

    for fname in field_names:
        f_obj: ExtractedField = getattr(extracted_data, fname, None)
        if f_obj is None:
            continue

        # Confidence bounds validation
        if f_obj.confidence_score is not None:
            clamped, c_warns = extraction_quality_service.validate_confidence_score(f_obj.confidence_score)
            f_obj.confidence_score = clamped
            for cw in c_warns:
                if cw not in f_obj.validation_warnings:
                    f_obj.validation_warnings.append(cw)
                if cw not in warnings:
                    warnings.append(cw)

        # Source reference traceability validation
        if f_obj.source_reference:
            validated_ref, s_warns = extraction_quality_service.validate_source_traceability(
                f_obj.source_reference, source_text
            )
            f_obj.source_reference = validated_ref
            for sw in s_warns:
                if sw not in f_obj.validation_warnings:
                    f_obj.validation_warnings.append(sw)
                if sw not in warnings:
                    warnings.append(sw)

    logger.info("Structured validation completed successfully.")
    return {
        "extracted_data": extracted_data,
        "validation_errors": validation_errors,
        "warnings": warnings,
        "workflow_status": "IN_PROGRESS",
    }
