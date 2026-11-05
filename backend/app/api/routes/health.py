"""Health check and readiness routing module for RootIQ."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.database.connection import check_database_connectivity
from app.services.ai_service import ai_service

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


@router.get(
    "/health/ready",
    summary="Service Readiness and Database Connectivity Probe",
    description="Validates database reachability. Returns HTTP 200 when ready, or HTTP 503 when the database is unavailable.",
)
async def get_readiness():
    """Readiness probe checking database connectivity."""
    is_ready, error_msg = check_database_connectivity()

    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unavailable",
                "database": "disconnected",
                "detail": error_msg or "Database connectivity check failed.",
                "application": settings.APP_NAME,
                "version": settings.APP_VERSION,
            },
        )

    return {
        "status": "ready",
        "database": "connected",
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get(
    "/health/ai",
    summary="AI Provider Connectivity and Model Verification Probe",
    description="Validates Groq API configuration and model responsiveness via a minimal harmless ping. Returns HTTP 200 when connected, or HTTP 503 when unconfigured or unreachable.",
)
async def get_ai_health():
    """Verify Groq API connectivity and model responsiveness."""
    result = ai_service.test_groq_connection()
    status_code = status.HTTP_200_OK if result["connected"] else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content=result,
    )
