"""Dashboard Business Service for RootIQ.

Calculates aggregated investigation and CAPA portfolio metrics directly
from the PostgreSQL database using SQL aggregations.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.capa import CapaAction
from app.models.investigation import Investigation
from app.schemas.capa import CAPAStatusEnum
from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.investigation import InvestigationStatusEnum


class DashboardService:
    """Service providing real-time PostgreSQL aggregated metrics for the quality dashboard."""

    def get_dashboard_summary(self, db: Session) -> DashboardSummaryResponse:
        """Query PostgreSQL database for aggregated portfolio indicators."""
        # Query investigation counts in a single grouped aggregation query
        inv_counts_stmt = select(
            Investigation.investigation_status,
            func.count(Investigation.id),
        ).group_by(Investigation.investigation_status)

        inv_counts = dict(db.execute(inv_counts_stmt).all())

        open_count = inv_counts.get(InvestigationStatusEnum.OPEN, 0)
        under_inv_count = inv_counts.get(InvestigationStatusEnum.UNDER_INVESTIGATION, 0)
        pending_capa_count = inv_counts.get(InvestigationStatusEnum.PENDING_REVIEW, 0)
        completed_count = inv_counts.get(InvestigationStatusEnum.CLOSED, 0)
        total_investigations = sum(inv_counts.values())

        # Query CAPA counts
        capa_counts_stmt = select(
            CapaAction.action_status,
            func.count(CapaAction.id),
        ).group_by(CapaAction.action_status)

        capa_counts = dict(db.execute(capa_counts_stmt).all())
        total_capa_actions = sum(capa_counts.values())

        # CAPA actions considered pending review: Proposed, Pending Review, or Draft
        pending_statuses = {
            CAPAStatusEnum.PROPOSED,
            CAPAStatusEnum.PENDING_REVIEW,
            CAPAStatusEnum.DRAFT,
        }
        capa_pending_review = sum(count for status, count in capa_counts.items() if status in pending_statuses)

        return DashboardSummaryResponse(
            total_investigations=total_investigations,
            open_investigations=open_count,
            investigations_under_investigation=under_inv_count,
            investigations_pending_capa=pending_capa_count,
            completed_investigations=completed_count,
            total_capa_actions=total_capa_actions,
            capa_actions_pending_review=capa_pending_review,
        )


# Singleton instance
dashboard_service = DashboardService()
