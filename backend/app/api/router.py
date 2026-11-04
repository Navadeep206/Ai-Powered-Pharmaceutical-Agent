"""Centralized API Router for RootIQ Backend Service.

Aggregates all sub-routers under the /api prefix.
"""

from fastapi import APIRouter
from app.api.routes import health

api_router = APIRouter(prefix="/api")

# Mount sub-routers
api_router.include_router(health.router)

__all__ = ["api_router"]

