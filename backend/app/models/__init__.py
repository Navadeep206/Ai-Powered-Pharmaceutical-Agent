"""SQLAlchemy ORM Domain Models for RootIQ.

Module responsible for pharmaceutical manufacturing quality investigations:
- Investigation: Lifecycle and stage tracking for API deviations and excursions.
- Document: File intake metadata, OCR requirements, and extracted narrative text.
- RCAAnalysis: Root cause analysis study (combining 5-Whys and Fishbone).
- FiveWhy: Individual causal links in a sequential 5-Whys analysis chain.
- FishboneCause: Ishikawa 6M causal factors with evidence citations and verification states.
- Evidence: Corroborating or contradictory evidence records and gap findings.
- CapaAction: Corrective and Preventive Action plans with ownership, deadlines, and verification.
- InvestigationActivity: GxP-compliant audit log entries tracking investigation events.
"""

from app.models.activity import InvestigationActivity
from app.models.capa import CapaAction
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.rca import FishboneCause, FiveWhy, RCAAnalysis

__all__ = [
    "Investigation",
    "Document",
    "RCAAnalysis",
    "FiveWhy",
    "FishboneCause",
    "Evidence",
    "CapaAction",
    "InvestigationActivity",
]
