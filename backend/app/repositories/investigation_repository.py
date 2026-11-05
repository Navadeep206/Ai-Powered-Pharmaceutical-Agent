"""SQLAlchemy 2.0 Repository for Investigation entity persistence."""

import uuid
from typing import Dict, List, Optional, Tuple, Union
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.models.investigation import Investigation
from app.schemas.investigation import InvestigationStatusEnum, SeverityEnum


class InvestigationRepository:
    """Encapsulates all database query and persistence logic for Investigations."""

    def create(self, db: Session, data: dict) -> Investigation:
        """Instantiate and persist a new Investigation record."""
        investigation = Investigation(**data)
        db.add(investigation)
        db.flush()
        return investigation

    def get_by_id(self, db: Session, identifier: Union[uuid.UUID, str]) -> Optional[Investigation]:
        """Retrieve an investigation by its primary key UUID or its unique investigation_number."""
        if isinstance(identifier, uuid.UUID):
            stmt = select(Investigation).where(Investigation.id == identifier)
            return db.scalars(stmt).first()

        # Identifier is a string: try parsing as UUID first
        try:
            parsed_uuid = uuid.UUID(str(identifier))
            stmt = select(Investigation).where(Investigation.id == parsed_uuid)
            res = db.scalars(stmt).first()
            if res is not None:
                return res
        except (ValueError, AttributeError):
            pass

        # Fallback to human-readable investigation_number (e.g., INV-2026-0001)
        stmt = select(Investigation).where(Investigation.investigation_number == str(identifier))
        return db.scalars(stmt).first()

    def get_by_number(self, db: Session, investigation_number: str) -> Optional[Investigation]:
        """Retrieve an investigation by unique human-readable tracking number."""
        stmt = select(Investigation).where(Investigation.investigation_number == investigation_number)
        return db.scalars(stmt).first()

    def list_paginated(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[InvestigationStatusEnum] = None,
        severity: Optional[SeverityEnum] = None,
        department: Optional[str] = None,
    ) -> Tuple[List[Investigation], int]:
        """Query paginated investigations with search and faceted filters."""
        stmt = select(Investigation)

        # Apply search term over key searchable text fields
        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Investigation.incident_title.ilike(term),
                    Investigation.incident_description.ilike(term),
                    Investigation.investigation_number.ilike(term),
                    Investigation.deviation_id.ilike(term),
                    Investigation.batch_number.ilike(term),
                    Investigation.product_name.ilike(term),
                )
            )

        if status:
            stmt = stmt.where(Investigation.investigation_status == status)

        if severity:
            stmt = stmt.where(Investigation.severity == severity)

        if department and department.strip():
            stmt = stmt.where(Investigation.department == department.strip())

        # Calculate total matching count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Apply ordering and pagination
        stmt = stmt.order_by(Investigation.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        items = list(db.scalars(stmt).all())
        return items, total

    def update(self, db: Session, investigation: Investigation, update_data: dict) -> Investigation:
        """Update fields on an existing investigation without overwriting unspecified fields."""
        for field, value in update_data.items():
            if hasattr(investigation, field) and value is not None:
                setattr(investigation, field, value)

        db.flush()
        return investigation

    def count_by_status(self, db: Session) -> Dict[str, int]:
        """Return counts of investigations grouped by lifecycle status."""
        stmt = select(
            Investigation.investigation_status,
            func.count(Investigation.id),
        ).group_by(Investigation.investigation_status)
        results = db.execute(stmt).all()
        return {str(status_val.value if hasattr(status_val, "value") else status_val): count for status_val, count in results}


# Singleton instance
investigation_repository = InvestigationRepository()
