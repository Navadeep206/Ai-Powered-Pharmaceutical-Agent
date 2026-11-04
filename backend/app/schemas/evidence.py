"""Pydantic schemas for investigation evidence and gap analysis."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EvidenceTypeEnum(str, Enum):
    """Categorization of evidence findings."""

    SUPPORTING = "Supporting"
    CONTRADICTORY = "Contradictory"
    MISSING_EVIDENCE = "Missing Evidence"
    INVESTIGATOR_QUESTION = "Investigator Question"


class EvidenceReviewStatusEnum(str, Enum):
    """Investigation review state for evidence items."""

    PENDING_REVIEW = "Pending Review"
    VERIFIED = "Verified"
    REJECTED = "Rejected"


class EvidenceCreate(BaseModel):
    """Payload for submitting new evidence item to an investigation."""

    description: str = Field(
        ...,
        min_length=5,
        description="Detailed description of the evidence observation or data point",
    )
    evidence_type: EvidenceTypeEnum = Field(
        ...,
        description="Type classification of this evidence",
    )
    source_reference: str = Field(
        ...,
        min_length=2,
        description="Batch record line, SCADA log file, calibration certificate, or SOP reference",
    )
    review_status: Optional[EvidenceReviewStatusEnum] = Field(
        default=EvidenceReviewStatusEnum.PENDING_REVIEW,
        description="Initial review status, defaults to Pending Review",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional investigator notes or evaluation context",
    )


class EvidenceResponse(BaseModel):
    """Structured response representing an evidence item."""

    evidence_id: str = Field(..., description="Unique evidence identifier (e.g. EVD-001)")
    investigation_id: str = Field(..., description="Associated investigation ID")
    description: str = Field(..., description="Evidence finding narrative")
    evidence_type: EvidenceTypeEnum = Field(..., description="Evidence type")
    source_reference: str = Field(..., description="Source document or data trail")
    review_status: EvidenceReviewStatusEnum = Field(..., description="Verification status")
    notes: Optional[str] = Field(default=None, description="Investigator notes")
    created_at: datetime = Field(..., description="Audit creation timestamp")

