"""Centralized API Router for RootIQ Backend Service.

Aggregates all domain sub-routers under the /api prefix:
- Health checks: /api/health
- Investigations: /api/investigations
- Documents: /api/documents
- RCA: /api/investigations/{investigation_id}/rca
- Evidence: /api/investigations/{investigation_id}/evidence
- CAPA: /api/investigations/{investigation_id}/capa
"""

from fastapi import APIRouter
from app.api.routes import (
    health,
    investigations,
    documents,
    rca,
    evidence,
    capa,
    dashboard,
)

api_router = APIRouter(prefix="/api")

# Mount sub-routers
api_router.include_router(health.router)
api_router.include_router(investigations.router)
api_router.include_router(documents.router)
api_router.include_router(rca.router)
api_router.include_router(evidence.router)
api_router.include_router(capa.router)
api_router.include_router(dashboard.router)

__all__ = ["api_router"]
