"""Schemas for AI extraction analysis and entity mapping."""

from datetime import date
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field
from app.schemas.investigation import SeverityEnum
from app.schemas.document import IntakeMethodEnum

T = TypeVar("T")


class ExtractedField(BaseModel, Generic[T]):
    """Encapsulates an AI-extracted candidate attribute with provenance and verification status."""

    field_name: str = Field(..., description="Canonical target attribute name")
    value: Optional[T] = Field(default=None, description="Extracted candidate value, or None if omitted")
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Heuristic extraction confidence score (0.0 - 1.0). Does NOT denote verified accuracy.",
    )
    source_reference: Optional[str] = Field(
        default=None,
        description="Text snippet, page number, or citation where value was extracted",
    )
    requires_human_review: bool = Field(
        default=True,
        description="Indicates this candidate field requires verification by a qualified investigator",
    )
    is_verified: bool = Field(
        default=False,
        description="Audit flag indicating whether a qualified investigator has confirmed the value",
    )


class IncidentExtractedData(BaseModel):
    """Structured extraction container for pharmaceutical deviation fields."""

    incident_title: ExtractedField[Optional[str]]
    incident_description: ExtractedField[Optional[str]]
    deviation_id: ExtractedField[Optional[str]]
    batch_number: ExtractedField[Optional[str]]
    product_name: ExtractedField[Optional[str]]
    department: ExtractedField[Optional[str]]
    equipment: ExtractedField[Optional[str]]
    incident_date: ExtractedField[Optional[date]]
    detection_date: ExtractedField[Optional[date]]
    severity: ExtractedField[Optional[SeverityEnum]]
    immediate_action_taken: ExtractedField[Optional[str]]
    expected_condition: ExtractedField[Optional[str]]
    actual_condition: ExtractedField[Optional[str]]
    observed_impact: ExtractedField[Optional[str]]
    affected_process: ExtractedField[Optional[str]]
    initial_observations: ExtractedField[Optional[str]]


class ExtractionAnalysisResponse(BaseModel):
    """Contract for AI-assisted intake analysis results."""

    analysis_id: str = Field(..., description="Tracking identifier for extraction run")
    intake_method: IntakeMethodEnum = Field(..., description="Source intake modality")
    extraction_status: str = Field(
        default="Pending Investigator Review",
        description="Lifecycle status of extraction process",
    )
    extracted_data: IncidentExtractedData = Field(
        ...,
        description="Extracted candidate attributes mapped to deviation structure",
    )
    missing_fields: List[str] = Field(
        default_factory=list,
        description="Critical fields not discovered in the source narrative",
    )
    fields_requiring_review: List[str] = Field(
        default_factory=list,
        description="Fields identified with low confidence or ambiguous source text",
    )
    disclaimer: str = Field(
        default="Extraction values are machine-generated recommendations and have NOT been verified by a qualified quality investigator.",
        description="Mandatory GxP non-repudiation and verification disclaimer",
    )

