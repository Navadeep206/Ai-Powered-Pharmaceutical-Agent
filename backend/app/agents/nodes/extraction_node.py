"""Incident extraction node for LangGraph workflow.

Invokes the existing ExtractionService and Groq client to extract structured
investigation fields while strictly preserving source references and confidence scores.
"""

from typing import Any, Dict
import groq
from app.agents.state import ExtractionWorkflowState
from app.core.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIConnectionError,
    AIModelUnavailableError,
    AIRateLimitError,
    AITimeoutError,
)
from app.core.logging import get_logger
from app.schemas.document import NormalizedIncidentIntake
from app.schemas.extraction import OverallExtractionStatus
from app.services.extraction_service import extraction_service

logger = get_logger("agents.nodes.extraction")


def incident_extraction_node(state: ExtractionWorkflowState) -> Dict[str, Any]:
    """Execute structured incident extraction using Groq via ExtractionService."""
    logger.info("Executing IncidentExtractionNode for workflow %s", state.get("workflow_id"))

    # Skip if previous node flagged failure
    if state.get("workflow_status") == "FAILED":
        return {}

    source_text = state.get("source_text") or ""
    source_type = state.get("source_type") or "Text"
    source_filename = state.get("source_filename")
    source_metadata = state.get("source_metadata") or {}
    page_refs = source_metadata.get("page_references") or []
    warnings = list(state.get("warnings") or [])

    # Check for early OCR condition
    if (
        source_metadata.get("processing_status") == "Preprocessing Completed (OCR Recommended)"
        or source_text.startswith("[NO EXTRACTABLE TEXT DETECTED IN PDF")
    ):
        logger.info("Source document flagged OCR_REQUIRED. Skipping LLM invocation.")
        empty_data = extraction_service._create_empty_extracted_data(source_type=source_type)
        return {
            "extracted_data": empty_data,
            "extraction_status": OverallExtractionStatus.OCR_REQUIRED.value,
            "warnings": warnings + [
                "Document appears to be a scanned image or lacks digital text. Optical Character Recognition (OCR) is required."
            ],
        }

    # Construct standard intake container for extraction service
    normalized_intake = NormalizedIncidentIntake(
        intake_id=state.get("workflow_id", "WF-EXTRACT"),
        source_type=source_type,
        source_filename=source_filename,
        prepared_incident_text=source_text,
        page_references=page_refs,
        processing_status=source_metadata.get("processing_status", "Ready for AI Analysis"),
    )

    try:
        extraction_res = extraction_service.extract_incident_information(
            normalized_intake=normalized_intake,
            raise_on_error=True,
        )

        return {
            "extracted_data": extraction_res.extracted_data,
            "extraction_status": (
                extraction_res.extraction_status.value
                if hasattr(extraction_res.extraction_status, "value")
                else str(extraction_res.extraction_status)
            ),
            "missing_fields": extraction_res.missing_fields,
            "ambiguous_fields": extraction_res.ambiguous_fields,
            "possible_contradictions": extraction_res.possible_contradictions,
            "critical_gaps": extraction_res.critical_gaps,
            "investigator_questions": extraction_res.investigator_questions,
            "completeness_score": extraction_res.completeness_score,
            "overall_confidence": extraction_res.overall_confidence,
            "warnings": list(set(warnings + extraction_res.warnings)),
            "extraction_response": extraction_res,
        }

    except (AIAuthenticationError, groq.AuthenticationError) as err:
        err_msg = f"Groq authentication failure: {err}"
        logger.error(err_msg)
        return {
            "workflow_status": "FAILED",
            "extraction_status": OverallExtractionStatus.FAILED.value,
            "error_message": err_msg,
            "warnings": warnings + [err_msg],
        }

    except (AITimeoutError, groq.APITimeoutError, TimeoutError) as err:
        err_msg = f"Groq API timeout: {err}"
        logger.error(err_msg)
        return {
            "workflow_status": "FAILED",
            "extraction_status": OverallExtractionStatus.FAILED.value,
            "error_message": err_msg,
            "warnings": warnings + [err_msg],
        }

    except (AIRateLimitError, groq.RateLimitError) as err:
        err_msg = f"Groq API rate limit exceeded: {err}"
        logger.error(err_msg)
        return {
            "workflow_status": "FAILED",
            "extraction_status": OverallExtractionStatus.FAILED.value,
            "error_message": err_msg,
            "warnings": warnings + [err_msg],
        }

    except (AIConfigurationError, AIModelUnavailableError, AIConnectionError, groq.BadRequestError) as err:
        err_msg = f"AI integration error: {err}"
        logger.error(err_msg)
        return {
            "workflow_status": "FAILED",
            "extraction_status": OverallExtractionStatus.FAILED.value,
            "error_message": err_msg,
            "warnings": warnings + [err_msg],
        }

    except Exception as err:
        err_msg = f"Unexpected error during extraction: {err}"
        logger.error(err_msg, exc_info=True)
        return {
            "workflow_status": "FAILED",
            "extraction_status": OverallExtractionStatus.FAILED.value,
            "error_message": err_msg,
            "warnings": warnings + [err_msg],
        }
