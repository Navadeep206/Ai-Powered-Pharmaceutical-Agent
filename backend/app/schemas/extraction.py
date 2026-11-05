"""Schemas for AI-assisted structured incident information extraction."""

from datetime import date
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field
from app.schemas.document import IntakeMethodEnum

T = TypeVar("T")


class FieldExtractionStatus(str, Enum):
    """Field-level extraction provenance state."""

    EXTRACTED = "EXTRACTED"
    MISSING = "MISSING"
    AMBIGUOUS = "AMBIGUOUS"
    INFERRED = "INFERRED"


class OverallExtractionStatus(str, Enum):
    """Lifecycle quality state of the complete incident extraction process."""

    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    OCR_REQUIRED = "OCR_REQUIRED"
    FAILED = "FAILED"


class SourceReference(BaseModel):
    """Provenance tracking identifying where a value was supported in source text."""

    source_type: Optional[str] = Field(default=None, description="Modality: Document, Text, or Email")
    page_number: Optional[int] = Field(default=None, description="1-indexed PDF page number, if available")
    excerpt: Optional[str] = Field(default=None, description="Verbatim text snippet from source")
    char_offset_start: Optional[int] = Field(
        default=None, description="Start character offset in normalized source text"
    )
    char_offset_end: Optional[int] = Field(
        default=None, description="End character offset in normalized source text"
    )


class ExtractedField(BaseModel, Generic[T]):
    """Encapsulates an AI-extracted candidate attribute with provenance and verification status."""

    field_name: str = Field(..., description="Canonical target attribute name")
    value: Optional[T] = Field(default=None, description="Extracted candidate value, or None if missing/unsupported")
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Heuristic extraction confidence score (0.0 - 1.0). Does NOT denote verified accuracy.",
    )
    source_reference: Optional[SourceReference] = Field(
        default=None,
        description="Text snippet, page number, or character offset where value was supported",
    )
    extraction_status: FieldExtractionStatus = Field(
        default=FieldExtractionStatus.MISSING,
        description="Field-level state: EXTRACTED, MISSING, AMBIGUOUS, INFERRED",
    )
    requires_human_review: bool = Field(
        default=True,
        description="Indicates candidate field requires verification by a qualified investigator",
    )
    is_verified: bool = Field(
        default=False,
        description="Audit flag indicating whether a qualified investigator has confirmed the value",
    )


class IncidentExtractedData(BaseModel):
    """Structured extraction container for pharmaceutical deviation fields."""

    # Incident identification
    incident_title: ExtractedField[Optional[str]] = Field(
        ..., description="Concise description of the deviation or excursion"
    )
    incident_description: ExtractedField[Optional[str]] = Field(
        ..., description="Comprehensive narrative detailing observed failure"
    )
    deviation_id: ExtractedField[Optional[str]] = Field(
        ..., description="Internal tracking ID (e.g. DEV-2026-0891)"
    )
    batch_number: ExtractedField[Optional[str]] = Field(
        ..., description="Manufacturing API batch or lot identifier (e.g. BATCH-9942A)"
    )
    product_name: ExtractedField[Optional[str]] = Field(
        ..., description="Product denomination or formulation name"
    )
    api_name: ExtractedField[Optional[str]] = Field(
        ..., description="Active Pharmaceutical Ingredient (API) chemical designation"
    )

    # Manufacturing context
    department: ExtractedField[Optional[str]] = Field(
        ..., description="Operational unit or department (e.g. Synthesis, Purification)"
    )
    equipment_id: ExtractedField[Optional[str]] = Field(
        ..., description="Machinery, reactor, or analytical instrument tag"
    )
    process_stage: ExtractedField[Optional[str]] = Field(
        ..., description="Unit operation or chemical manufacturing step"
    )
    incident_date: ExtractedField[Optional[str]] = Field(
        ..., description="Date when excursion occurred (ISO-8601 YYYY-MM-DD)"
    )
    detection_date: ExtractedField[Optional[str]] = Field(
        ..., description="Date when excursion was first detected by operator or system"
    )

    # Incident details
    expected_condition: ExtractedField[Optional[str]] = Field(
        ..., description="Validated parameter range or standard operating condition"
    )
    actual_condition: ExtractedField[Optional[str]] = Field(
        ..., description="Observed empirical condition during excursion"
    )
    immediate_action_taken: ExtractedField[Optional[str]] = Field(
        ..., description="Immediate containment actions taken to mitigate excursion"
    )
    potential_impact: ExtractedField[Optional[str]] = Field(
        ..., description="Observed or potential impact on product quality, safety, or yield"
    )
    observations: ExtractedField[Optional[str]] = Field(
        ..., description="Preliminary notes recorded by operators or initial investigators"
    )

    # Additional extracted context
    detection_method: ExtractedField[Optional[str]] = Field(
        ..., description="How anomaly was detected (e.g. SCADA Alarm, In-Process Control assay, Visual)"
    )
    personnel_roles_involved: ExtractedField[Optional[List[str]]] = Field(
        ..., description="Roles or job titles mentioned in incident narrative"
    )
    relevant_measurements: ExtractedField[Optional[List[Dict[str, Any]]]] = Field(
        ..., description="Quantified parameter readings, assays, or sensory metrics with units"
    )
    relevant_operating_parameters: ExtractedField[Optional[List[Dict[str, Any]]]] = Field(
        ..., description="Key operating ranges, pressure, agitation, pH, or temperature limits"
    )

    # Backward compatibility aliases for investigation mapping
    @property
    def equipment(self) -> ExtractedField[Optional[str]]:
        return self.equipment_id

    @property
    def affected_process(self) -> ExtractedField[Optional[str]]:
        return self.process_stage

    @property
    def observed_impact(self) -> ExtractedField[Optional[str]]:
        return self.potential_impact

    @property
    def initial_observations(self) -> ExtractedField[Optional[str]]:
        return self.observations


class ExtractionAnalysisResponse(BaseModel):
    """Contract for AI-assisted intake analysis results."""

    analysis_id: str = Field(..., description="Tracking identifier for extraction run")
    intake_method: IntakeMethodEnum = Field(..., description="Source intake modality")
    extraction_status: OverallExtractionStatus = Field(
        default=OverallExtractionStatus.NEEDS_REVIEW,
        description="Lifecycle status: COMPLETED, PARTIALLY_COMPLETED, NEEDS_REVIEW, OCR_REQUIRED, FAILED",
    )
    extracted_data: IncidentExtractedData = Field(
        ...,
        description="Extracted candidate attributes mapped to deviation structure",
    )
    missing_fields: List[str] = Field(
        default_factory=list,
        description="Required or important fields not discovered in the source narrative",
    )
    ambiguous_fields: List[str] = Field(
        default_factory=list,
        description="Fields identified with contradictory or uncertain source text",
    )
    fields_requiring_review: List[str] = Field(
        default_factory=list,
        description="Fields requiring review due to ambiguity, low confidence, or GxP criticality",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Quality, completeness, or data integrity warnings",
    )
    extraction_summary: Optional[str] = Field(
        default=None,
        description="Executive summary of the extraction outcome and evidence gaps",
    )
    overall_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average confidence across extracted fields",
    )
    disclaimer: str = Field(
        default="Extraction values are machine-generated recommendations from source text and have NOT been verified by a qualified quality investigator. GxP regulations require human confirmation.",
        description="Mandatory GxP non-repudiation and verification disclaimer",
    )
