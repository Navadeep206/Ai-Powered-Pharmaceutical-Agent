"""SQLAlchemy 2.0 Repository for Investigation Activities (Audit Trail History)."""

import uuid
from typing import List, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.activity import InvestigationActivity


class ActivityRepository:
    """Encapsulates recording and retrieval of investigation application events."""

    def create(self, db: Session, data: dict) -> InvestigationActivity:
        """Record an application event in the investigation activity history."""
        activity = InvestigationActivity(**data)
        db.add(activity)
        db.flush()
        return activity

    def list_by_investigation(
        self,
        db: Session,
        investigation_id: Union[uuid.UUID, str],
        limit: int = 50,
    ) -> List[InvestigationActivity]:
        """Fetch the chronological activity log for an investigation."""
        if not isinstance(investigation_id, uuid.UUID):
            try:
                investigation_id = uuid.UUID(str(investigation_id))
            except (ValueError, AttributeError):
                return []
        stmt = (
            select(InvestigationActivity)
            .where(InvestigationActivity.investigation_id == investigation_id)
            .order_by(InvestigationActivity.created_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt).all())


# Singleton instance
activity_repository = ActivityRepository()

