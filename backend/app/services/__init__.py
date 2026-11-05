"""Business Logic & Service Layer for RootIQ.

Orchestrates core domain workflows decoupled from transport and storage layers:
- DocumentService: Safe PDF validation, in-memory parsing, and OCR requirement detection.
- IntakeService: Normalization of multi-modal intake (PDF, pasted text, email).
- InvestigationService: Workflow transitions, state progression, and approval gates.
- RCAService: Coordination between 5-Whys, 6M Fishbone, and verification gates.
- EvidenceService: Evidence ingestion, parsing, and correlation indexing.
- CAPAService: CAPA tracking, status progression, and effectiveness verification.
"""

from app.services.document_service import DocumentService, document_service
from app.services.intake_service import IntakeService, intake_service
from app.services.investigation_service import InvestigationService, investigation_service
from app.services.rca_service import RCAService, rca_service
from app.services.evidence_service import EvidenceService, evidence_service
from app.services.capa_service import CAPAService, capa_service
from app.services.dashboard_service import DashboardService, dashboard_service
from app.services.ai_service import AIService, ai_service
from app.services.extraction_service import ExtractionService, extraction_service

__all__ = [
    "DocumentService",
    "document_service",
    "IntakeService",
    "intake_service",
    "InvestigationService",
    "investigation_service",
    "RCAService",
    "rca_service",
    "EvidenceService",
    "evidence_service",
    "CAPAService",
    "capa_service",
    "DashboardService",
    "dashboard_service",
    "AIService",
    "ai_service",
    "ExtractionService",
    "extraction_service",
]
