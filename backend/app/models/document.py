"""SQLAlchemy ORM model for uploaded incident documents and extraction metadata."""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base
from app.schemas.document import IntakeMethodEnum


class Document(Base):
    """Uploaded incident file metadata and text extraction result."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    investigation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="Associated investigation ID, if attached",
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Relative path or storage key if retained",
    )
    content_type: Mapped[str] = mapped_column(String(100), nullable=False, default="application/pdf")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_type: Mapped[IntakeMethodEnum] = mapped_column(
        SAEnum(IntakeMethodEnum, name="intake_method_enum", native_enum=False),
        nullable=False,
        default=IntakeMethodEnum.DOCUMENT,
    )
    extraction_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Pending",
        comment="Status: Success, Partial Extraction (OCR Required), OCR Required, or Failed",
    )
    extracted_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Normalized text content extracted from document",
    )
    page_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Granular page-by-page character counts and OCR requirements",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    investigation: Mapped[Optional["Investigation"]] = relationship(
        "Investigation",
        back_populates="documents",
    )
