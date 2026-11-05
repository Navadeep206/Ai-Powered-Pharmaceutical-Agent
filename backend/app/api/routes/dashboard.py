"""Executive and Operational Dashboard route definitions for RootIQ."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.dashboard import DashboardSummaryResponse
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

