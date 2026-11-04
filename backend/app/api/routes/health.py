"""Health check routing module."""

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service Health Status")
async def get_health():
    """Health check endpoint.

    Returns the operational status of the service without external
    dependencies (PostgreSQL, Groq).
    """
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }

