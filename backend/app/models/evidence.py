"""SQLAlchemy ORM model for investigation evidence records and verification status."""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base
from app.schemas.evidence import EvidenceReviewStatusEnum, EvidenceTypeEnum


class Evidence(Base):
    """Investigation evidence observation, batch record citation, or interview excerpt."""

    __tablename__ = "evidence_records"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Associated quality investigation ID",
    )
    evidence_type: Mapped[EvidenceTypeEnum] = mapped_column(
        SAEnum(EvidenceTypeEnum, name="evidence_type_enum", native_enum=False),
        nullable=False,
        comment="Classification: Supporting, Contradictory, Missing Evidence, Investigator Question",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Detailed finding, data observation, or testimonial excerpt",
    )
    source_reference: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Document reference, batch record line, SCADA tag, or calibration log ID",
    )
    review_status: Mapped[EvidenceReviewStatusEnum] = mapped_column(
        SAEnum(EvidenceReviewStatusEnum, name="evidence_review_status_enum", native_enum=False),
        nullable=False,
        default=EvidenceReviewStatusEnum.PENDING_REVIEW,
        comment="Verification state: Pending Review, Verified, or Rejected",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Investigator evaluation notes or follow-up rationale",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="evidence_records",
    )

    __table_args__ = (
        Index("ix_evidence_investigation_type", "investigation_id", "evidence_type"),
    )

