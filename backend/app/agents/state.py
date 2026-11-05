"""LangGraph State Architecture for RootIQ Incident Extraction and RCA Reasoning.

Defines the strongly typed state containers tracking the full lifecycle:
1. Incident intake, extraction, validation, and quality assessment.
2. Root Cause Analysis (5-Whys, 6M Fishbone, Evidence Classification, and Root Cause Synthesis).
Maintains strict separation between operational workflow status and domain verification.
"""

from typing import Any, Dict, List, Optional, TypedDict

from app.schemas.extraction import (
    CriticalGapItem,
    ExtractionAnalysisResponse,
    IncidentExtractedData,
    PossibleContradiction,
)
from app.schemas.rca import (
    ContributingFactor,
    EvidenceAssessment,
    FishboneCause,
    FiveWhysLevel,
    PotentialRootCause,
    RCAWorkflowResult,
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
    workflow_status: str  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    extraction_status: str  # COMPLETED, PARTIALLY_COMPLETED, NEEDS_REVIEW, OCR_REQUIRED, FAILED
    error_message: Optional[str]
    warnings: List[str]

    # Retry management
    retry_count: int
    max_retries: int

    # Timing & Observability
    processing_started_at: str
    processing_completed_at: Optional[str]
    duration_seconds: Optional[float]


class RCAWorkflowState(ExtractionWorkflowState, total=False):
    """Extended LangGraph state for AI-assisted Root Cause Analysis reasoning."""

    # Contextual inputs for RCA
    problem_statement: str
    incident_context: Dict[str, Any]
    investigation_facts: List[Dict[str, Any]]
    evidence_records: List[Dict[str, Any]]

    # RCA Core Reasoning Outputs
    five_whys_analysis: List[FiveWhysLevel]
    fishbone_analysis: List[FishboneCause]
    potential_root_causes: List[PotentialRootCause]
    contributing_factors: List[ContributingFactor]

    # Evidence Evaluation & Classification
    supporting_evidence: List[EvidenceAssessment]
    contradictory_evidence: List[EvidenceAssessment]
    missing_evidence: List[str]

    # Domain State & Safeguards
    rca_warnings: List[str]
    rca_status: str  # Draft, Needs Review, Completed, Failed
    human_review_required: bool  # Strict GxP verification gate (always True until human approval)
    persisted_in_db: bool
    rca_analysis_id: Optional[str]

    # Final Synthesized RCA Result
    rca_workflow_result: Optional[RCAWorkflowResult]
