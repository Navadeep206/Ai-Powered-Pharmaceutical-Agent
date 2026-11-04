"""Schemas for document upload and multi-modal incident intake."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class IntakeMethodEnum(str, Enum):
    """Supported multi-modal incident intake mechanisms."""

    DOCUMENT = "Document"
    TEXT = "Text"
    EMAIL = "Email"


class DocumentUploadResponse(BaseModel):
    """Response returned upon document file receipt."""

    document_id: str = Field(..., description="Unique transient or stored document tracking ID")
    filename: str = Field(..., description="Original client filename")
    file_size_bytes: int = Field(..., ge=0, description="Payload size in bytes")
    content_type: str = Field(..., description="MIME content type, expected application/pdf")
    uploaded_at: datetime = Field(..., description="Timestamp of document receipt")
    status: str = Field(default="Uploaded", description="Processing lifecycle state")


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
    """Consolidated request for initiating document or narrative extraction."""

    intake_method: IntakeMethodEnum = Field(..., description="Selected intake channel")
    document_id: Optional[str] = Field(
        default=None,
        description="Referenced document ID when intake_method is Document",
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
        if self.intake_method == IntakeMethodEnum.DOCUMENT and not self.document_id:
            raise ValueError("document_id is required when intake_method is 'Document'")
        if self.intake_method == IntakeMethodEnum.TEXT and not self.text_input:
            raise ValueError("text_input is required when intake_method is 'Text'")
        if self.intake_method == IntakeMethodEnum.EMAIL and not self.email_input:
            raise ValueError("email_input is required when intake_method is 'Email'")
        return self
