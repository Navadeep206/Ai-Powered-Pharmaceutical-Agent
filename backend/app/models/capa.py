"""SQLAlchemy ORM model for Corrective and Preventive Actions (CAPA)."""

import uuid
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base
from app.schemas.capa import CAPAStatusEnum, CAPATypeEnum


class CapaAction(Base):
    """CAPA remediation or preventive action plan tied to an investigation and root cause."""

    __tablename__ = "capa_actions"

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
        comment="Associated quality investigation",
    )
    related_root_cause_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("fishbone_causes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Specific root cause factor this action resolves",
    )
    action_type: Mapped[CAPATypeEnum] = mapped_column(
        SAEnum(CAPATypeEnum, name="capa_type_enum", native_enum=False),
        nullable=False,
        comment="Action classification: Corrective Action or Preventive Action",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Specific operational, procedural, engineering, or training remediation",
    )
    action_owner: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Assigned responsible engineer, supervisor, or department lead",
    )
    target_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Mandatory completion target date",
    )
    effectiveness_verification: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Empirical protocol to verify that the cause was eliminated and excursion does not recur",
    )
    action_status: Mapped[CAPAStatusEnum] = mapped_column(
        SAEnum(CAPAStatusEnum, name="capa_status_enum", native_enum=False),
        nullable=False,
        default=CAPAStatusEnum.DRAFT,
        index=True,
        comment="Lifecycle status: Draft, Proposed, Approved, In Progress, Completed, or Closed",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when implementation was verified and closed",
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
        back_populates="capa_actions",
    )
    related_root_cause: Mapped[Optional["FishboneCause"]] = relationship(
        "FishboneCause",
        back_populates="related_capa_actions",
    )

    __table_args__ = (
        Index("ix_capa_investigation_status", "investigation_id", "action_status"),
        Index("ix_capa_target_date", "target_date"),
    )

