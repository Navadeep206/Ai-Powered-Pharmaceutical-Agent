"""Pydantic schemas for Root Cause Analysis (5-Whys, 6M Fishbone, Evidence Analysis, and RCA Workflow)."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from app.schemas.evidence import EvidenceReviewStatusEnum, EvidenceTypeEnum


class FishboneCategoryEnum(str, Enum):
    """The Ishikawa 6M classification categories for pharmaceutical manufacturing."""

    MANPOWER = "Manpower"
    MACHINE = "Machine"
    METHOD = "Method"
    MATERIAL = "Material"
    MEASUREMENT = "Measurement"
    ENVIRONMENT = "Environment"


class CauseVerificationStatusEnum(str, Enum):
    """Rigorous classification for RCA findings to avoid conflating AI drafts with confirmed causes."""

    AI_SUGGESTION = "AI Suggestion"
    EVIDENCE_SUPPORTED = "Evidence Supported"
    HUMAN_REVIEWED = "Human Reviewed"
    CONFIRMED_ROOT_CAUSE = "Confirmed Root Cause"
    RULED_OUT = "Ruled Out"


class FiveWhysLevel(BaseModel):
    """Single step in a 5-Whys causal chain."""

    level: int = Field(..., ge=1, le=5, description="Sequential level 1 through 5")
    question: str = Field(..., min_length=3, description="Interrogative question focusing on upstream failure")
    answer: str = Field(..., min_length=2, description="Causal answer backed by technical context")
    reasoning: Optional[str] = Field(default=None, description="Technical rationale supporting this answer")
    evidence_references: List[str] = Field(
        default_factory=list,
        description="IDs or citations of attached evidence supporting this causal step",
    )
    supporting_evidence_references: List[str] = Field(
        default_factory=list,
        description="Alias for evidence_references",
    )
    confidence: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Confidence score for this causal link (0.0 to 1.0)",
    )
    uncertainty_notes: Optional[str] = Field(
        default=None,
        description="Specific uncertainties, assumptions, or missing data points",
    )
    is_root_cause: bool = Field(
        default=False,
        description="Flag denoting this level as the designated root cause",
    )
    status: CauseVerificationStatusEnum = Field(
        default=CauseVerificationStatusEnum.AI_SUGGESTION,
        description="Verification state of this causal step (must not auto-confirm without human approval)",
    )

    @model_validator(mode="before")
    @classmethod
    def reconcile_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "why_number" in data and "level" not in data:
                data["level"] = data["why_number"]
            if "proposed_answer" in data and "answer" not in data:
                data["answer"] = data["proposed_answer"]
            if "review_status" in data and "status" not in data:
                data["status"] = data["review_status"]
            if "supporting_evidence_references" in data and not data.get("evidence_references"):
                data["evidence_references"] = data["supporting_evidence_references"]
            elif "evidence_references" in data and not data.get("supporting_evidence_references"):
                data["supporting_evidence_references"] = data["evidence_references"]
        return data

    @property
    def why_number(self) -> int:
        return self.level

    @property
    def proposed_answer(self) -> str:
        return self.answer

    @property
    def review_status(self) -> CauseVerificationStatusEnum:
        return self.status


class FishboneCause(BaseModel):
    """Potential or verified causal factor mapped to the 6M Ishikawa diagram."""

    cause_id: str = Field(..., description="Unique cause identifier (e.g. CAUSE-01)")
    category: FishboneCategoryEnum = Field(..., description="Ishikawa 6M category")
    cause_description: str = Field(..., min_length=3, description="Detailed hypothesis or observed causal factor")
    reasoning: Optional[str] = Field(default=None, description="Technical rationale supporting this cause")
    evidence_references: List[str] = Field(
        default_factory=list,
        description="Associated evidence IDs validating or disputing this cause",
    )
    supporting_evidence_references: List[str] = Field(
        default_factory=list,
        description="Associated evidence citations supporting this cause",
    )
    contradictory_evidence_references: List[str] = Field(
        default_factory=list,
        description="Associated evidence citations challenging or contradicting this cause",
    )
    confidence: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Confidence score for this causal link (0.0 to 1.0)",
    )
    cause_origin: str = Field(
        default="AI Suggestion",
        description="'AI Suggestion', 'Investigator Added', or 'Telemetry Inferred'",
    )
    status: CauseVerificationStatusEnum = Field(
        default=CauseVerificationStatusEnum.AI_SUGGESTION,
        description="Verification status; AI suggestions remain unconfirmed until human review",
    )
    uncertainty_notes: Optional[str] = Field(
        default=None,
        description="Uncertainties or assumptions regarding this cause",
    )
    contributing_factors: List[str] = Field(
        default_factory=list,
        description="Secondary sub-branches under this main branch cause",
    )

    @model_validator(mode="before")
    @classmethod
    def reconcile_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "review_status" in data and "status" not in data:
                data["status"] = data["review_status"]
            if "supporting_evidence_references" in data and not data.get("evidence_references"):
                data["evidence_references"] = data["supporting_evidence_references"]
            elif "evidence_references" in data and not data.get("supporting_evidence_references"):
                data["supporting_evidence_references"] = data["evidence_references"]
        return data

    @property
    def review_status(self) -> CauseVerificationStatusEnum:
        return self.status


class EvidenceAssessment(BaseModel):
    """Structured evidence assessment evaluating factual support or contradictions for RCA causes."""

    evidence_id: str = Field(..., description="Unique evidence identifier (e.g. EVD-001)")
    evidence_description: str = Field(..., min_length=3, description="Description of evidence finding or data point")
    evidence_type: EvidenceTypeEnum = Field(
        ...,
        description="Classification: Supporting, Contradictory, Missing Evidence, Investigator Question",
    )
    source_reference: Optional[str] = Field(
        default=None,
        description="Source document citation, SCADA tag, or test result",
    )
    related_potential_cause: Optional[str] = Field(
        default=None,
        description="Associated causal hypothesis or Why level",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Why this evidence supports, disputes, or identifies gaps for the cause",
    )
    confidence: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Confidence in this evidence evaluation",
    )
    review_status: EvidenceReviewStatusEnum = Field(
        default=EvidenceReviewStatusEnum.PENDING_REVIEW,
        description="Verification state",
    )

    @property
    def description(self) -> str:
        return self.evidence_description


class PotentialRootCause(BaseModel):
    """Synthesized plausible root cause candidate supported by evidence."""

    cause_id: str = Field(..., description="Identifier for candidate cause (e.g. PRC-01)")
    cause_description: str = Field(..., min_length=3, description="Detailed statement of the potential root cause")
    cause_category: str = Field(..., description="Classification or Ishikawa 6M category")
    source_method: str = Field(..., description="'Five Whys', 'Fishbone', or 'Combined'")
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Citations or descriptions of supporting evidence",
    )
    contradictory_evidence: List[str] = Field(
        default_factory=list,
        description="Citations or descriptions of contradictory evidence",
    )
    confidence: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Confidence score",
    )
    rationale: str = Field(..., description="Detailed technical justification for designating this candidate")
    uncertainty_notes: Optional[str] = Field(default=None, description="Unresolved questions or gaps")
    review_status: CauseVerificationStatusEnum = Field(
        default=CauseVerificationStatusEnum.AI_SUGGESTION,
        description="Review status (must remain AI Suggestion or Evidence Supported until human confirmation)",
    )


class ContributingFactor(BaseModel):
    """Identified secondary or environmental factor contributing to deviation occurrence."""

    factor_id: str = Field(..., description="Identifier (e.g. CF-01)")
    description: str = Field(..., min_length=3, description="Description of contributing condition")
    category: str = Field(..., description="Category (e.g. Manpower, Machine, Method, Environment)")
    related_cause_id: Optional[str] = Field(default=None, description="Related primary root cause ID if applicable")
    supporting_evidence: List[str] = Field(default_factory=list, description="Supporting evidence citations")


class RCAGenerateRequest(BaseModel):
    """Optional configuration or context payload for AI-assisted RCA generation."""

    problem_statement: Optional[str] = Field(
        default=None,
        description="Explicit problem statement. If omitted, will be formulated from incident context.",
    )
    incident_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context regarding equipment, batch, process parameters, or observations.",
    )
    investigation_facts: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Known factual data points (e.g. SCADA tags, temperature readings, timeline events).",
    )
    persist: bool = Field(
        default=True,
        description="Whether to persist generated RCA and evidence records to PostgreSQL.",
    )


class RCARequest(BaseModel):
    """Request payload to save or update RCA findings for an investigation."""

    five_whys: List[FiveWhysLevel] = Field(
        default_factory=list,
        description="5-Whys causal investigation tree",
    )
    fishbone_causes: List[FishboneCause] = Field(
        default_factory=list,
        description="Collection of categorized Ishikawa 6M causes",
    )
    investigator_notes: Optional[str] = Field(
        default=None,
        description="Synthesis notes and rationale provided by lead investigator",
    )


class RCAResponse(BaseModel):
    """Complete RCA assessment response for an investigation."""

    investigation_id: str = Field(..., description="Associated investigation ID")
    five_whys: List[FiveWhysLevel] = Field(..., description="Ordered 5-Whys chain")
    fishbone_causes: List[FishboneCause] = Field(..., description="Ishikawa 6M causal factors")
    investigator_notes: Optional[str] = Field(default=None, description="Investigator notes")
    updated_at: datetime = Field(..., description="Audit timestamp of last RCA update")


class RCAWorkflowResult(BaseModel):
    """Complete AI-assisted RCA reasoning result synthesized by LangGraph workflow."""

    workflow_id: str = Field(..., description="Workflow execution ID")
    investigation_id: Optional[str] = Field(default=None, description="Investigation ID")
    problem_statement: str = Field(
        ...,
        description="Concise, verified problem statement formulated from incident context",
    )
    five_whys_analysis: List[FiveWhysLevel] = Field(default_factory=list, description="Sequence of Why levels")
    fishbone_analysis: List[FishboneCause] = Field(default_factory=list, description="Ishikawa 6M causes")
    evidence_assessment: List[EvidenceAssessment] = Field(default_factory=list, description="Classified evidence items")
    potential_root_causes: List[PotentialRootCause] = Field(
        default_factory=list, description="Synthesized candidate root causes"
    )
    contributing_factors: List[ContributingFactor] = Field(
        default_factory=list, description="Identified secondary contributing factors"
    )
    missing_evidence: List[str] = Field(
        default_factory=list, description="Critical evidence gaps needed to confirm causes"
    )
    investigator_questions: List[str] = Field(
        default_factory=list, description="Specific follow-up inquiries for investigation team"
    )
    rca_warnings: List[str] = Field(default_factory=list, description="Causal and evidence warnings")
    rca_status: str = Field(default="Needs Review", description="RCA lifecycle status")
    human_review_required: bool = Field(
        default=True,
        description="Strict GxP flag: requires human quality investigator confirmation",
    )
    persisted_in_db: bool = Field(default=False, description="Whether records were persisted to PostgreSQL")
    analysis_id: Optional[str] = Field(default=None, description="PostgreSQL RCAAnalysis record ID if persisted")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of result generation",
    )
