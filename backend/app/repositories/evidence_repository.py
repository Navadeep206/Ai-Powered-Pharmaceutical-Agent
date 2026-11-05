"""SQLAlchemy 2.0 Repository for Evidence records persistence."""

import uuid
from typing import List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.evidence import Evidence


class EvidenceRepository:
    """Encapsulates database operations for investigation evidence items."""

    def create(self, db: Session, data: dict) -> Evidence:
        """Persist a new Evidence record."""
        evidence = Evidence(**data)
        db.add(evidence)
        db.flush()
        return evidence

    def get_by_id(self, db: Session, evidence_id: Union[uuid.UUID, str]) -> Optional[Evidence]:
        """Fetch an evidence record by its primary key UUID."""
        if not isinstance(evidence_id, uuid.UUID):
            try:
                evidence_id = uuid.UUID(str(evidence_id))
            except (ValueError, AttributeError):
                return None
        stmt = select(Evidence).where(Evidence.id == evidence_id)
        return db.scalars(stmt).first()

    def list_by_investigation(
        self,
        db: Session,
        investigation_id: Union[uuid.UUID, str],
    ) -> List[Evidence]:
        """Fetch all evidence items linked to an investigation, sorted newest first."""
        if not isinstance(investigation_id, uuid.UUID):
            try:
                investigation_id = uuid.UUID(str(investigation_id))
            except (ValueError, AttributeError):
                return []
        stmt = select(Evidence).where(Evidence.investigation_id == investigation_id).order_by(Evidence.created_at.desc())
        return list(db.scalars(stmt).all())


# Singleton instance
evidence_repository = EvidenceRepository()
