"""Pydantic schemas for Corrective and Preventive Actions (CAPA)."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CAPATypeEnum(str, Enum):
    """CAPA action classifications under ICH Q10."""

    CORRECTIVE_ACTION = "Corrective Action"
    PREVENTIVE_ACTION = "Preventive Action"


class CAPAStatusEnum(str, Enum):
    """Lifecycle states of CAPA actions."""

    DRAFT = "Draft"
    PROPOSED = "Proposed"
    APPROVED = "Approved"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CLOSED = "Closed"


class CAPACreate(BaseModel):
    """Payload to propose a new CAPA action."""

    action_type: CAPATypeEnum = Field(..., description="Classification as Corrective or Preventive action")
    description: str = Field(
        ...,
        min_length=10,
        description="Detailed specification of remediation or preventive procedure",
    )
    action_owner: str = Field(
        ...,
        min_length=2,
        description="Assigned responsible role, engineer, or department head",
    )
    target_date: date = Field(
        ...,
        description="Target completion date for implementation",
    )
    effectiveness_verification_method: str = Field(
        ...,
        min_length=10,
        description="Empirical protocol to verify that the root cause was eliminated and excursion does not recur",
    )
    status: Optional[CAPAStatusEnum] = Field(
        default=CAPAStatusEnum.DRAFT,
        description="Initial lifecycle status; defaults to Draft and cannot be auto-marked Approved or Completed",
    )
    related_root_cause_reference: Optional[str] = Field(
        default=None,
        description="Causal factor or 5-Whys level ID this action directly remediates",
    )


class CAPAResponse(BaseModel):
    """Structured response for a CAPA action record."""

    action_id: str = Field(..., description="Unique CAPA identifier (e.g. CAPA-001)")
    investigation_id: str = Field(..., description="Associated investigation ID")
    action_type: CAPATypeEnum = Field(..., description="Action classification")
    description: str = Field(..., description="Action specification")
    action_owner: str = Field(..., description="Responsible individual or department")
    target_date: date = Field(..., description="Target completion date")
    effectiveness_verification_method: str = Field(..., description="Verification protocol")
    status: CAPAStatusEnum = Field(..., description="Current lifecycle state")
    related_root_cause_reference: Optional[str] = Field(default=None, description="Linked root cause reference")
    created_at: datetime = Field(..., description="Creation audit timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")

