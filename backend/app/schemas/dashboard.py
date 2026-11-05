"""Pydantic schemas for executive dashboard metrics."""

from pydantic import BaseModel, Field


class DashboardSummaryResponse(BaseModel):
    """Aggregated portfolio metrics derived directly from PostgreSQL database."""

    total_investigations: int = Field(..., ge=0, description="Total investigations logged in the system")
    open_investigations: int = Field(..., ge=0, description="Active investigations in Open status")
    investigations_under_investigation: int = Field(
        ..., ge=0, description="Investigations actively undergoing root cause analysis"
    )
    investigations_pending_capa: int = Field(
        ..., ge=0, description="Investigations awaiting CAPA proposal or approval (Pending Review)"
    )
    completed_investigations: int = Field(..., ge=0, description="Investigations closed and verified under GxP")
    total_capa_actions: int = Field(..., ge=0, description="Total CAPA actions recorded across all investigations")
    capa_actions_pending_review: int = Field(
        ..., ge=0, description="CAPA actions pending review, draft, or proposed approval"
    )

