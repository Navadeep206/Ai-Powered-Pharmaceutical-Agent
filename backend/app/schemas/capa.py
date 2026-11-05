"""Pydantic schemas for Corrective and Preventive Actions (CAPA)."""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.rca import PotentialRootCause


class CAPATypeEnum(str, Enum):
    """CAPA action classifications under ICH Q10."""

    CORRECTIVE_ACTION = "Corrective Action"
    PREVENTIVE_ACTION = "Preventive Action"


class CAPAStatusEnum(str, Enum):
    """Lifecycle states of CAPA actions."""

    DRAFT = "Draft"
    PROPOSED = "Proposed"
    PENDING_REVIEW = "Pending Review"
    APPROVED = "Approved"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    REJECTED = "Rejected"
    CLOSED = "Closed"


class EffectivenessVerificationPlan(BaseModel):
    """Structured effectiveness verification protocol for a CAPA under FDA/ICH Q10."""

    measurable_outcome: str = Field(
        ...,
        min_length=5,
        description="Specific, quantifiable, or verifiable criteria demonstrating failure mode elimination",
    )
    verification_method: str = Field(
        ...,
        min_length=5,
        description="Inspection, testing, audit, sampling protocol, or analytical assay to be applied",
    )
    evidence_required: str = Field(
        ...,
        min_length=5,
        description="Documentary evidence required (e.g. 3 consecutive batch records, calibration cert, lab assay)",
    )
    suggested_verifier_role: str = Field(
        ...,
        min_length=2,
        description="Suggested role responsible for verification (e.g. QA Compliance Specialist, Engineering Manager)",
    )
    verification_timeframe: str = Field(
        ...,
        min_length=3,
        description="Evaluation duration or monitoring window (e.g. 'Next 5 commercial batches' or '90 days post-implementation')",
    )
    failure_criteria: str = Field(
        ...,
        min_length=5,
        description="Condition or threshold indicating unsuccessful remediation requiring CAPA reopening",
    )


class CAPARecommendation(BaseModel):
    """AI-generated or human-edited Corrective or Preventive Action recommendation."""

    capa_id: str = Field(..., description="Unique recommendation identifier (e.g. CAPA-REC-01)")
    action_type: CAPATypeEnum = Field(..., description="Classification as Corrective Action or Preventive Action")
    description: str = Field(..., min_length=10, description="Specific and actionable remediation or prevention description")
    related_root_cause_id: Optional[str] = Field(default=None, description="Linked potential root cause or contributing factor ID")
    rationale: str = Field(..., min_length=5, description="Technical justification explaining how this action resolves the causal condition")
    supporting_evidence_references: List[str] = Field(default_factory=list, description="Associated evidence or data points")
    assumptions: List[str] = Field(default_factory=list, description="Documented operational or engineering assumptions")
    dependencies: List[str] = Field(default_factory=list, description="Prerequisite changes, equipment downtime, or SOP revisions")
    suggested_owner_role: str = Field(..., min_length=2, description="Suggested organizational role (not an invented individual)")
    suggested_target_date: Optional[str] = Field(default=None, description="Suggested completion timeframe (e.g. '+30 days')")
    effectiveness_verification: EffectivenessVerificationPlan = Field(..., description="Structured verification protocol")
    review_status: CAPAStatusEnum = Field(default=CAPAStatusEnum.PROPOSED, description="Initial review status (Proposed or Pending Review)")
    assigned_owner: Optional[str] = Field(default=None, description="Actual assigned human owner assigned during review")
    actual_target_date: Optional[date] = Field(default=None, description="Actual completion deadline set by human reviewer")
    reviewer_comments: Optional[str] = Field(default=None, description="Comments, conditions, or modifications from reviewer")
    reviewed_at: Optional[datetime] = Field(default=None, description="Timestamp of review decision")
    reviewed_by: Optional[str] = Field(default=None, description="Reviewer actor identifier (unauthenticated in this phase)")


class CAPAGenerateRequest(BaseModel):
    """Request payload to initiate AI-assisted CAPA recommendations."""

    problem_statement: Optional[str] = Field(default=None, description="Optional problem statement override")
    persist: bool = Field(default=True, description="Whether to persist generated suggestions to PostgreSQL as PENDING_REVIEW")


class CAPAReviewItemDecision(BaseModel):
    """Human review decision for an individual CAPA recommendation."""

    capa_id: str = Field(..., description="Identifier of the CAPA recommendation to review")
    decision: CAPAStatusEnum = Field(..., description="Decision: APPROVED, REJECTED, PROPOSED, or PENDING_REVIEW")
    edited_description: Optional[str] = Field(default=None, description="Optional revised description")
    edited_action_type: Optional[CAPATypeEnum] = Field(default=None, description="Optional modified action type")
    assigned_owner: Optional[str] = Field(default=None, description="Assigned human owner or confirmed role")
    target_date: Optional[date] = Field(default=None, description="Confirmed target completion date")
    edited_effectiveness_plan: Optional[EffectivenessVerificationPlan] = Field(default=None, description="Revised verification protocol")
    reviewer_comments: Optional[str] = Field(default=None, description="Reviewer justification or notes")
    reviewer_identifier: Optional[str] = Field(default="QA Reviewer", description="Unauthenticated actor identifier")


class CAPAReviewRequest(BaseModel):
    """Payload submitted to review, approve, reject, or edit CAPA recommendations."""

    thread_id: Optional[str] = Field(default=None, description="LangGraph checkpoint thread ID if resuming paused workflow")
    decisions: List[CAPAReviewItemDecision] = Field(..., min_length=1, description="Decisions for individual recommendations")
    general_comments: Optional[str] = Field(default=None, description="General reviewer comments for the investigation")
    reviewer_identifier: Optional[str] = Field(default="QA Lead", description="Unauthenticated reviewer identifier")


class CAPAWorkflowResult(BaseModel):
    """Complete result of CAPA generation, validation, and human review workflow."""

    workflow_id: str = Field(..., description="Workflow execution ID")
    investigation_id: Optional[str] = Field(default=None, description="Associated investigation ID")
    thread_id: str = Field(..., description="LangGraph checkpoint thread ID")
    rca_summary: Optional[str] = Field(default=None, description="RCA problem and systemic causal findings")
    potential_root_causes: List[PotentialRootCause] = Field(default_factory=list, description="Underlying root cause candidates")
    capa_recommendations: List[CAPARecommendation] = Field(default_factory=list, description="All CAPA recommendations")
    corrective_actions: List[CAPARecommendation] = Field(default_factory=list, description="Corrective action items")
    preventive_actions: List[CAPARecommendation] = Field(default_factory=list, description="Preventive action items")
    approved_actions: List[CAPARecommendation] = Field(default_factory=list, description="Actions approved by human reviewer")
    rejected_actions: List[CAPARecommendation] = Field(default_factory=list, description="Actions rejected by human reviewer")
    pending_actions: List[CAPARecommendation] = Field(default_factory=list, description="Actions still awaiting human review")
    validation_errors: List[str] = Field(default_factory=list, description="Validation issues flagged by CAPA validation node")
    capa_warnings: List[str] = Field(default_factory=list, description="Operational and causal warnings")
    capa_generation_status: str = Field(default="PENDING", description="AI generation status: PENDING, COMPLETED, FAILED")
    capa_review_status: str = Field(default="PENDING_REVIEW", description="Review state: PENDING_REVIEW, APPROVED, REJECTED, PARTIAL")
    human_review_required: bool = Field(default=True, description="Strict GxP gate: requires human QA sign-off")
    workflow_completion_status: str = Field(default="PAUSED_FOR_HUMAN_REVIEW", description="Lifecycle: PAUSED_FOR_HUMAN_REVIEW, COMPLETED, FAILED")
    persisted_in_db: bool = Field(default=False, description="Whether records were persisted to PostgreSQL")
    persisted_capa_ids: List[str] = Field(default_factory=list, description="IDs of CapaAction records persisted in PostgreSQL")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of result generation")


class CAPAStatusUpdate(BaseModel):
    """Payload to update the lifecycle status of an existing CAPA action."""

    status: CAPAStatusEnum = Field(..., description="Target lifecycle state")
    notes: Optional[str] = Field(default=None, description="Optional reviewer rationale or verification notes")


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


