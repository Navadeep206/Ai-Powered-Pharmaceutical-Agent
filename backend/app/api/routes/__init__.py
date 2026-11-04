"""API Route Modules for RootIQ."""

from app.api.routes.health import router as health_router
from app.api.routes.investigations import router as investigations_router
from app.api.routes.documents import router as documents_router
from app.api.routes.rca import router as rca_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.capa import router as capa_router

__all__ = [
    "health_router",
    "investigations_router",
    "documents_router",
    "rca_router",
    "evidence_router",
    "capa_router",
]
