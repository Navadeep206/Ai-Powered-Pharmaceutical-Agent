"""Input processing and validation node for LangGraph incident extraction workflow.

Validates source text presence, source modality, and initializes workflow status
without invoking external LLMs.
"""

from typing import Any, Dict
from app.agents.state import ExtractionWorkflowState
from app.core.logging import get_logger
from app.schemas.document import IntakeMethodEnum

logger = get_logger("agents.nodes.input")

SUPPORTED_SOURCE_TYPES = {
    IntakeMethodEnum.DOCUMENT.value,
    IntakeMethodEnum.TEXT.value,
    IntakeMethodEnum.EMAIL.value,
    "Document",
    "Text",
    "Email",
}


def input_processing_node(state: ExtractionWorkflowState) -> Dict[str, Any]:
    """Validate input text, source modality, and initialize workflow execution state."""
    logger.info("Executing InputProcessingNode for workflow %s", state.get("workflow_id"))

    source_text = state.get("source_text") or ""
    source_type = state.get("source_type") or ""
    validation_errors = list(state.get("validation_errors") or [])
    warnings = list(state.get("warnings") or [])

    # 1. Validate source type
    if source_type not in SUPPORTED_SOURCE_TYPES:
        err_msg = f"Unsupported source type '{source_type}'. Must be one of: Document, Text, Email."
        logger.error("Input processing failed: %s", err_msg)
        validation_errors.append(err_msg)
        return {
            "workflow_status": "FAILED",
            "extraction_status": "FAILED",
            "error_message": err_msg,
            "validation_errors": validation_errors,
        }

    # 2. Validate source text existence and length
    clean_text = source_text.strip()
    if not clean_text:
        err_msg = "Source incident text cannot be empty or contain only whitespace."
        logger.error("Input processing failed: %s", err_msg)
        validation_errors.append(err_msg)
        return {
            "workflow_status": "FAILED",
            "extraction_status": "FAILED",
            "error_message": err_msg,
            "validation_errors": validation_errors,
        }

    if len(clean_text) < 15:
        warn_msg = "Source text is very brief (under 15 characters). Extraction quality may be degraded."
        warnings.append(warn_msg)

    # 3. Successful input validation
    logger.info(
        "Input validated successfully for modality '%s' (%d characters).",
        source_type,
        len(clean_text),
    )
    return {
        "workflow_status": "IN_PROGRESS",
        "warnings": warnings,
        "validation_errors": validation_errors,
    }
