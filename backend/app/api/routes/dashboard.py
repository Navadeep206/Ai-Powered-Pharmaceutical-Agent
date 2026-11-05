"""Executive and Operational Dashboard route definitions for RootIQ."""

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.dashboard import DashboardActivityResponse, DashboardSummaryResponse
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get aggregated dashboard metrics",
    description="Calculates portfolio key performance indicators (total deviations, active RCA, pending CAPA, closed investigations) directly from PostgreSQL aggregation queries.",
)
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """Derives live quality metrics directly from database state."""
    return dashboard_service.get_dashboard_summary(db=db)


@router.get(
    "/activities",
    response_model=List[DashboardActivityResponse],
    summary="Get recent audit activities across investigations",
    description="Retrieves the most recent audit trail events across all quality investigations from PostgreSQL.",
)
async def get_dashboard_activities(
    limit: int = Query(default=10, ge=1, le=50, description="Max number of activities to return"),
    db: Session = Depends(get_db),
):
    """Derives live activity log directly from database state."""
    return dashboard_service.get_recent_activities(db=db, limit=limit)


