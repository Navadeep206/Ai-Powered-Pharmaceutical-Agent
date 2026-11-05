"""SQLAlchemy 2.0 Repository for Document entity persistence."""

import uuid
from typing import List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.document import Document


class DocumentRepository:
    """Encapsulates database operations for document intake metadata."""

    def create(self, db: Session, data: dict) -> Document:
        """Persist document metadata for an intake file or extracted text artifact."""
        document = Document(**data)
        db.add(document)
        db.flush()
        return document

    def get_by_id(self, db: Session, document_id: Union[uuid.UUID, str]) -> Optional[Document]:
        """Retrieve document metadata by UUID."""
        if not isinstance(document_id, uuid.UUID):
            try:
                document_id = uuid.UUID(str(document_id))
            except (ValueError, AttributeError):
                return None
        stmt = select(Document).where(Document.id == document_id)
        return db.scalars(stmt).first()

    def list_by_investigation(
        self,
        db: Session,
        investigation_id: Union[uuid.UUID, str],
    ) -> List[Document]:
        """Retrieve all documents attached to an investigation."""
        if not isinstance(investigation_id, uuid.UUID):
            try:
                investigation_id = uuid.UUID(str(investigation_id))
            except (ValueError, AttributeError):
                return []
        stmt = select(Document).where(Document.investigation_id == investigation_id).order_by(Document.created_at.desc())
        return list(db.scalars(stmt).all())


# Singleton instance
document_repository = DocumentRepository()

