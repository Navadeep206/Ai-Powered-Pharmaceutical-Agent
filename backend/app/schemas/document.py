"""Schemas for document upload, extraction results, and incident intake."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class IntakeMethodEnum(str, Enum):
    """Supported multi-modal incident intake mechanisms."""

    DOCUMENT = "Document"
    TEXT = "Text"
    EMAIL = "Email"


class PageExtractionResult(BaseModel):
    """Granular extraction result for an individual PDF page."""

    page_number: int = Field(..., ge=1, description="1-indexed page number")
    text: str = Field(default="", description="Extracted text content from this page")
    character_count: int = Field(default=0, ge=0, description="Number of extracted characters")
    has_text: bool = Field(default=False, description="Whether page contains extractable digital text")
    requires_ocr: bool = Field(
        default=False,
        description="Flag indicating page contains no text stream and requires optical character recognition",
    )


class DocumentExtractionResult(BaseModel):
    """Structured result returned from real PDF document parsing."""

    document_id: str = Field(..., description="Unique transient tracking identifier")
    original_filename: str = Field(..., description="Sanitized client filename")
    file_size_bytes: int = Field(..., ge=0, description="File size in bytes")
    number_of_pages: int = Field(..., ge=0, description="Total page count")
    extracted_text: str = Field(default="", description="Consolidated document text across all pages")
    page_wise_content: List[PageExtractionResult] = Field(
        default_factory=list,
        description="Page-by-page extracted content and OCR detection",
    )
    extraction_status: str = Field(
        default="Success",
        description="Lifecycle status: 'Success', 'Partial Extraction (OCR Required)', 'OCR Required', or 'Failed'",
    )
    pages_requiring_ocr: List[int] = Field(
        default_factory=list,
        description="List of 1-indexed page numbers that contain no machine-readable text",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Informational or data integrity warnings encountered during extraction",
    )


# Retain DocumentUploadResponse for backward compatibility
class DocumentUploadResponse(DocumentExtractionResult):
    """Response returned upon document file receipt and extraction."""

    pass


class TextIncidentInput(BaseModel):
    """Intake schema for raw pasted incident descriptions."""

    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional title provided by reporter",
    )
    incident_text: str = Field(
        ...,
        min_length=15,
        description="Comprehensive freeform narrative describing the deviation excursion",
    )
    department: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional department context",
    )


class EmailIncidentInput(BaseModel):
    """Intake schema for emailed deviation reports."""

    subject: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Subject line of deviation notification email",
    )
    body: str = Field(
        ...,
        min_length=15,
        description="Full email body containing deviation particulars",
    )
    sender: Optional[str] = Field(
        default=None,
        description="Sender email address for audit trace",
    )


class DocumentAnalysisRequest(BaseModel):
    """Consolidated request for initiating document or narrative intake preprocessing."""

    intake_method: IntakeMethodEnum = Field(..., description="Selected intake channel")
    document_id: Optional[str] = Field(
        default=None,
        description="Referenced document ID when intake_method is Document",
    )
    document_text: Optional[str] = Field(
        default=None,
        description="Optional pre-extracted document text passed from client or previous step",
    )
    text_input: Optional[TextIncidentInput] = Field(
        default=None,
        description="Narrative payload when intake_method is Text",
    )
    email_input: Optional[EmailIncidentInput] = Field(
        default=None,
        description="Email payload when intake_method is Email",
    )

    @model_validator(mode="after")
    def validate_matching_payload(self) -> "DocumentAnalysisRequest":
        """Ensure the specified intake method matches provided payload content."""
        if self.intake_method == IntakeMethodEnum.DOCUMENT and not self.document_id and not self.document_text:
            raise ValueError("document_id or document_text is required when intake_method is 'Document'")
        if self.intake_method == IntakeMethodEnum.TEXT and not self.text_input:
            raise ValueError("text_input is required when intake_method is 'Text'")
        if self.intake_method == IntakeMethodEnum.EMAIL and not self.email_input:
            raise ValueError("email_input is required when intake_method is 'Email'")
        return self


class PageReference(BaseModel):
    """Page reference mapping within normalized incident intake."""

    page_number: int = Field(..., ge=1)
    character_count: int = Field(default=0)
    has_text: bool = Field(default=True)
    requires_ocr: bool = Field(default=False)


class NormalizedIncidentIntake(BaseModel):
    """Normalized incident input structure ready for downstream AI analysis."""

    intake_id: str = Field(..., description="Unique tracking identifier for this intake preprocessing run")
    source_type: IntakeMethodEnum = Field(..., description="Originating intake modality")
    source_filename: Optional[str] = Field(
        default=None,
        description="Original document filename if intake was Document",
    )
    subject: Optional[str] = Field(
        default=None,
        description="Subject line if intake was Email or title if Text",
    )
    prepared_incident_text: str = Field(
        ...,
        description="Sanitized, normalized, and consolidated text content ready for AI ingestion",
    )
    page_references: List[PageReference] = Field(
        default_factory=list,
        description="Page metadata if intake originated from a PDF document",
    )
    processing_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings regarding missing text, OCR recommendations, or formatting quirks",
    )
    processing_status: str = Field(
        default="Ready for AI Analysis",
        description="Preprocessing state: 'Ready for AI Analysis' or 'Preprocessing Completed (OCR Recommended)'",
    )
    processed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of preprocessing execution",
    )
    disclaimer: str = Field(
        default="Input information has been preprocessed and normalized for AI investigation workflows. AI entity extraction has NOT yet been executed.",
        description="Mandatory GxP notice indicating this is preprocessed source material",
    )
