"""Pydantic Request and Response Schemas for RootIQ API.

Enforces strict type validation and serialization for API boundaries:
- Common schemas (pagination, response envelopes, error structures)
- Investigation schemas (creation, update, response, list)
- Document & Extraction schemas (upload, text intake, email intake, AI extraction analysis)
- RCA schemas (5-Whys causal chains, Ishikawa 6M fishbone models)
- Evidence schemas (supporting, contradictory, missing, investigator questions)
- CAPA schemas (corrective and preventive actions, effectiveness verification)
"""

from app.schemas.common import (
    PaginationMetadata,
    PaginatedResponse,
    StandardResponse,
    SuccessResponse,
    ErrorResponse,
)
from app.schemas.investigation import (
    SeverityEnum,
    InvestigationStatusEnum,
    InvestigationBase,
    InvestigationCreate,
    InvestigationUpdate,
    InvestigationResponse,
    InvestigationListResponse,
)
from app.schemas.document import (
    IntakeMethodEnum,
    PageExtractionResult,
    DocumentExtractionResult,
    DocumentUploadResponse,
    DocumentMetadataResponse,
    TextIncidentInput,
    EmailIncidentInput,
    DocumentAnalysisRequest,
    PageReference,
    NormalizedIncidentIntake,
)
from app.schemas.extraction import (
    FieldExtractionStatus,
    OverallExtractionStatus,
    ReviewStatusEnum,
    SourceReference,
    PossibleContradiction,
    CriticalGapItem,
    ExtractedField,
    IncidentExtractedData,
    ExtractionAnalysisResponse,
)
from app.schemas.rca import (
    FishboneCategoryEnum,
    CauseVerificationStatusEnum,
    FiveWhysLevel,
    FishboneCause,
    EvidenceAssessment,
    PotentialRootCause,
    ContributingFactor,
    RCAGenerateRequest,
    RCARequest,
    RCAResponse,
    RCAWorkflowResult,
)
from app.schemas.evidence import (
    EvidenceTypeEnum,
    EvidenceReviewStatusEnum,
    EvidenceCreate,
    EvidenceResponse,
)
from app.schemas.capa import (
    CAPATypeEnum,
    CAPAStatusEnum,
    EffectivenessVerificationPlan,
    CAPARecommendation,
    CAPAGenerateRequest,
    CAPAReviewItemDecision,
    CAPAReviewRequest,
    CAPAWorkflowResult,
    CAPACreate,
    CAPAResponse,
    CAPAStatusUpdate,
)
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    DashboardActivityResponse,
)

__all__ = [
    # Common
    "PaginationMetadata",
    "PaginatedResponse",
    "StandardResponse",
    "SuccessResponse",
    "ErrorResponse",
    # Investigation
    "SeverityEnum",
    "InvestigationStatusEnum",
    "InvestigationBase",
    "InvestigationCreate",
    "InvestigationUpdate",
    "InvestigationResponse",
    "InvestigationListResponse",
    # Document
    "IntakeMethodEnum",
    "PageExtractionResult",
    "DocumentExtractionResult",
    "DocumentUploadResponse",
    "DocumentMetadataResponse",
    "TextIncidentInput",
    "EmailIncidentInput",
    "DocumentAnalysisRequest",
    "PageReference",
    "NormalizedIncidentIntake",
    # Extraction
    "FieldExtractionStatus",
    "OverallExtractionStatus",
    "ReviewStatusEnum",
    "SourceReference",
    "PossibleContradiction",
    "CriticalGapItem",
    "ExtractedField",
    "IncidentExtractedData",
    "ExtractionAnalysisResponse",
    # RCA
    "FishboneCategoryEnum",
    "CauseVerificationStatusEnum",
    "FiveWhysLevel",
    "FishboneCause",
    "EvidenceAssessment",
    "PotentialRootCause",
    "ContributingFactor",
    "RCAGenerateRequest",
    "RCARequest",
    "RCAResponse",
    "RCAWorkflowResult",
    # Evidence
    "EvidenceTypeEnum",
    "EvidenceReviewStatusEnum",
    "EvidenceCreate",
    "EvidenceResponse",
    # CAPA
    "CAPATypeEnum",
    "CAPAStatusEnum",
    "EffectivenessVerificationPlan",
    "CAPARecommendation",
    "CAPAGenerateRequest",
    "CAPAReviewItemDecision",
    "CAPAReviewRequest",
    "CAPAWorkflowResult",
    "CAPACreate",
    "CAPAResponse",
    "CAPAStatusUpdate",
    # Dashboard
    "DashboardSummaryResponse",
    "DashboardActivityResponse",
]
