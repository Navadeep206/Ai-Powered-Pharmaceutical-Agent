"""SQLAlchemy 2.0 Repository for CAPA action plan persistence."""

import uuid
from typing import Dict, List, Optional, Union
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.capa import CapaAction


class CAPARepository:
    """Encapsulates database operations for Corrective and Preventive Actions."""

    def create(self, db: Session, data: dict) -> CapaAction:
        """Persist a new CAPA action record."""
        capa = CapaAction(**data)
        db.add(capa)
        db.flush()
        return capa

    def get_by_id(self, db: Session, capa_id: Union[uuid.UUID, str]) -> Optional[CapaAction]:
        """Fetch a CAPA action by its primary key UUID."""
        if not isinstance(capa_id, uuid.UUID):
            try:
                capa_id = uuid.UUID(str(capa_id))
            except (ValueError, AttributeError):
                return None
        stmt = select(CapaAction).where(CapaAction.id == capa_id)
        return db.scalars(stmt).first()

    def list_by_investigation(
        self,
        db: Session,
        investigation_id: Union[uuid.UUID, str],
    ) -> List[CapaAction]:
        """Fetch all CAPA actions linked to an investigation, sorted newest first."""
        if not isinstance(investigation_id, uuid.UUID):
            try:
                investigation_id = uuid.UUID(str(investigation_id))
            except (ValueError, AttributeError):
                return []
        stmt = select(CapaAction).where(CapaAction.investigation_id == investigation_id).order_by(CapaAction.created_at.desc())
        return list(db.scalars(stmt).all())

    def list_all(
        self,
        db: Session,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[CapaAction]:
        """Fetch all CAPA actions across all investigations, sorted newest first."""
        from sqlalchemy.orm import joinedload
        from sqlalchemy import or_

        stmt = select(CapaAction).options(joinedload(CapaAction.investigation))

        if status and status.strip() and status.upper() != "ALL":
            stmt = stmt.where(CapaAction.action_status == status)

        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    CapaAction.description.ilike(term),
                    CapaAction.action_owner.ilike(term),
                    CapaAction.effectiveness_verification.ilike(term),
                )
            )

        stmt = stmt.order_by(CapaAction.created_at.desc()).offset(offset).limit(limit)
        return list(db.scalars(stmt).unique().all())

    def update(self, db: Session, capa: CapaAction, update_data: dict) -> CapaAction:
        """Update fields on an existing CAPA action."""
        for field, value in update_data.items():
            if hasattr(capa, field) and value is not None:
                setattr(capa, field, value)
        db.flush()
        return capa

    def count_by_status(self, db: Session) -> Dict[str, int]:
        """Return counts of CAPA actions grouped by lifecycle status."""
        stmt = select(
            CapaAction.action_status,
            func.count(CapaAction.id),
        ).group_by(CapaAction.action_status)
        results = db.execute(stmt).all()
        return {str(status_val.value if hasattr(status_val, "value") else status_val): count for status_val, count in results}


# Singleton instance
capa_repository = CAPARepository()

