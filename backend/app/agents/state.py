"""LangGraph State Architecture for RootIQ Incident Extraction Workflow.

Defines the strongly typed state container tracking the lifecycle of an incident
investigation intake, extraction, Pydantic validation, and quality assessment.
Maintains strict separation between operational workflow status and domain extraction quality.
"""

from typing import Any, Dict, List, Optional, TypedDict

from app.schemas.extraction import (
    CriticalGapItem,
    ExtractionAnalysisResponse,
    IncidentExtractedData,
    PossibleContradiction,
)


class ExtractionWorkflowState(TypedDict, total=False):
    """Strongly typed LangGraph state for incident information extraction workflow."""

    # Workflow tracking & identity
    workflow_id: str
    investigation_id: Optional[str]
    thread_id: str

    # Source intake & metadata (no secrets or raw binaries)
    source_type: str  # Document, Text, Email
    source_text: str  # Normalized text payload
    source_filename: Optional[str]
    source_metadata: Dict[str, Any]

    # Extraction artifacts
    raw_extraction: Optional[Dict[str, Any]]
    extracted_data: Optional[IncidentExtractedData]
    extraction_response: Optional[ExtractionAnalysisResponse]

    # Validation & Quality assessment
    validation_errors: List[str]
    missing_fields: List[str]
    critical_gaps: List[str]
    ambiguous_fields: List[str]
    possible_contradictions: List[PossibleContradiction]
    investigator_questions: List[str]
    completeness_score: float
    overall_confidence: float

    # Status & Error tracking
    # workflow_status represents orchestration execution: PENDING, IN_PROGRESS, COMPLETED, FAILED
    workflow_status: str
    # extraction_status represents domain GxP quality: COMPLETED, PARTIALLY_COMPLETED, NEEDS_REVIEW, OCR_REQUIRED, FAILED
    extraction_status: str
    error_message: Optional[str]
    warnings: List[str]

    # Retry management
    retry_count: int
    max_retries: int

    # Timing & Observability
    processing_started_at: str
    processing_completed_at: Optional[str]
    duration_seconds: Optional[float]
