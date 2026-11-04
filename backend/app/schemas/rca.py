"""Pydantic schemas for Root Cause Analysis (5-Whys and 6M Fishbone)."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


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
    evidence_references: List[str] = Field(
        default_factory=list,
        description="IDs or citations of attached evidence supporting this causal step",
    )
    is_root_cause: bool = Field(
        default=False,
        description="Flag denoting this level as the primary systemic root cause",
    )
    status: CauseVerificationStatusEnum = Field(
        default=CauseVerificationStatusEnum.AI_SUGGESTION,
        description="Verification state of this causal step (must not auto-confirm without human approval)",
    )


class FishboneCause(BaseModel):
    """Potential or verified causal factor mapped to the 6M Ishikawa diagram."""

    cause_id: str = Field(..., description="Unique cause identifier (e.g. CAUSE-01)")
    category: FishboneCategoryEnum = Field(..., description="Ishikawa 6M category")
    cause_description: str = Field(..., min_length=3, description="Detailed hypothesis or observed causal factor")
    evidence_references: List[str] = Field(
        default_factory=list,
        description="Associated evidence IDs validating or disputing this cause",
    )
    status: CauseVerificationStatusEnum = Field(
        default=CauseVerificationStatusEnum.AI_SUGGESTION,
        description="Verification status; AI suggestions remain unconfirmed until human review",
    )
    contributing_factors: List[str] = Field(
        default_factory=list,
        description="Secondary sub-branches under this main branch cause",
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
