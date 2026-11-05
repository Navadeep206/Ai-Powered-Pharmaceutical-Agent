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
    SourceReference,
    ExtractedField,
    IncidentExtractedData,
    ExtractionAnalysisResponse,
)
from app.schemas.rca import (
    FishboneCategoryEnum,
    CauseVerificationStatusEnum,
    FiveWhysLevel,
    FishboneCause,
    RCARequest,
    RCAResponse,
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
    CAPACreate,
    CAPAResponse,
    CAPAStatusUpdate,
)
from app.schemas.dashboard import (
    DashboardSummaryResponse,
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
    "SourceReference",
    "ExtractedField",
    "IncidentExtractedData",
    "ExtractionAnalysisResponse",
    # RCA
    "FishboneCategoryEnum",
    "CauseVerificationStatusEnum",
    "FiveWhysLevel",
    "FishboneCause",
    "RCARequest",
    "RCAResponse",
    # Evidence
    "EvidenceTypeEnum",
    "EvidenceReviewStatusEnum",
    "EvidenceCreate",
    "EvidenceResponse",
    # CAPA
    "CAPATypeEnum",
    "CAPAStatusEnum",
    "CAPACreate",
    "CAPAResponse",
    "CAPAStatusUpdate",
    # Dashboard
    "DashboardSummaryResponse",
]
