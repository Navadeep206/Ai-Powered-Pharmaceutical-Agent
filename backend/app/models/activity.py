"""SQLAlchemy ORM model for investigation audit trail activities."""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base


class InvestigationActivity(Base):
    """GxP-compliant audit log entry tracking events and state changes across an investigation."""

    __tablename__ = "investigation_activities"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated quality investigation",
    )
    activity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Event type: 'CREATED', 'STATUS_CHANGE', 'DOCUMENT_UPLOAD', 'RCA_UPDATED', 'CAPA_ADDED', etc.",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable summary of the recorded action",
    )
    actor_identifier: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        default="System",
        comment="User ID, investigator username, or autonomous agent identifier",
    )
    # The database column is named 'metadata', but mapped to 'activity_metadata' in Python
    # to avoid conflicting with DeclarativeBase.metadata.
    activity_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        comment="Structured payload of previous/current values or contextual event data",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="activities",
    )

    __table_args__ = (
        Index("ix_activities_investigation_created", "investigation_id", "created_at"),
    )

