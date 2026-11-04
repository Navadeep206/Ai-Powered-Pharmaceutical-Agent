"""Pydantic schemas for quality investigation management."""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import PaginationMetadata


class SeverityEnum(str, Enum):
    """GxP critical deviation severity ratings."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class InvestigationStatusEnum(str, Enum):
    """Quality investigation lifecycle statuses."""

    OPEN = "Open"
    UNDER_INVESTIGATION = "Under Investigation"
    PENDING_REVIEW = "Pending Review"
    CLOSED = "Closed"


class InvestigationBase(BaseModel):
    """Shared attributes across investigation payloads."""

    incident_title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Concise description of the deviation or quality failure",
    )
    incident_description: str = Field(
        ...,
        min_length=10,
        description="Comprehensive narrative detailing deviation context and observed failure",
    )
    deviation_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Internal corporate deviation tracking identifier (e.g. DEV-2026-0891)",
    )
    batch_number: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Manufacturing API batch or lot identifier (e.g. BATCH-9942A)",
    )
    product_name: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Active Pharmaceutical Ingredient (API) or product denomination",
    )
    department: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Operational department (e.g. Synthesis, Quality Assurance, Purification)",
    )
    equipment: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Specific machinery, reactor, or analytical instrument ID",
    )
    incident_date: Optional[date] = Field(
        default=None,
        description="Date when the physical excursion or anomaly occurred",
    )
    detection_date: Optional[date] = Field(
        default=None,
        description="Date when the anomaly was first detected by operator or system",
    )
    severity: SeverityEnum = Field(
        ...,
        description="GxP risk severity classification",
    )
    immediate_action_taken: Optional[str] = Field(
        default=None,
        description="Containment actions executed immediately to prevent further contamination or excursion",
    )
    expected_condition: Optional[str] = Field(
        default=None,
        description="Standard operating parameter or validated operating range",
    )
    actual_condition: Optional[str] = Field(
        default=None,
        description="Observed empirical condition or parameter measurement during excursion",
    )
    observed_impact: Optional[str] = Field(
        default=None,
        description="Direct impact on product quality, safety, efficacy, or regulatory compliance",
    )
    affected_process: Optional[str] = Field(
        default=None,
        description="Unit operation or chemical manufacturing step involved",
    )
    initial_observations: Optional[str] = Field(
        default=None,
        description="Preliminary notes recorded by initial investigators",
    )


class InvestigationCreate(InvestigationBase):
    """Schema for initiating a new quality deviation investigation."""

    investigation_status: Optional[InvestigationStatusEnum] = Field(
        default=InvestigationStatusEnum.OPEN,
        description="Initial lifecycle status, defaults to Open",
    )


class InvestigationUpdate(BaseModel):
    """Schema for partial update (PATCH) of an ongoing investigation."""

    incident_title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    incident_description: Optional[str] = Field(default=None, min_length=10)
    deviation_id: Optional[str] = Field(default=None, max_length=64)
    batch_number: Optional[str] = Field(default=None, max_length=64)
    product_name: Optional[str] = Field(default=None, max_length=128)
    department: Optional[str] = Field(default=None, max_length=100)
    equipment: Optional[str] = Field(default=None, max_length=100)
    incident_date: Optional[date] = Field(default=None)
    detection_date: Optional[date] = Field(default=None)
    severity: Optional[SeverityEnum] = Field(default=None)
    immediate_action_taken: Optional[str] = Field(default=None)
    expected_condition: Optional[str] = Field(default=None)
    actual_condition: Optional[str] = Field(default=None)
    observed_impact: Optional[str] = Field(default=None)
    affected_process: Optional[str] = Field(default=None)
    initial_observations: Optional[str] = Field(default=None)
    investigation_status: Optional[InvestigationStatusEnum] = Field(default=None)


class InvestigationResponse(InvestigationBase):
    """Complete representation of a quality investigation."""

    investigation_id: str = Field(
        ...,
        description="Unique system investigation identifier (e.g. INV-2026-001)",
    )
    investigation_status: InvestigationStatusEnum = Field(
        ...,
        description="Current lifecycle status",
    )
    created_at: datetime = Field(
        ...,
        description="Audit-compliant creation timestamp",
    )
    updated_at: datetime = Field(
        ...,
        description="Last modification timestamp",
    )


class InvestigationListResponse(BaseModel):
    """Response containing a paginated list of investigations."""

    items: List[InvestigationResponse] = Field(..., description="Array of investigation records")
    pagination: PaginationMetadata = Field(..., description="Pagination metadata")

