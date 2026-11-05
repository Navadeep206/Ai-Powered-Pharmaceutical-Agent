"""SQLAlchemy ORM model for quality deviation investigations."""

import uuid
from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import Date, DateTime, Enum as SAEnum, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base
from app.schemas.investigation import InvestigationStatusEnum, SeverityEnum


class Investigation(Base):
    """Quality investigation entity representing a pharmaceutical deviation or excursion."""

    __tablename__ = "investigations"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    investigation_number: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Human-readable unique tracking identifier (e.g. INV-2026-0001)",
    )

    # Incident information
    incident_title: Mapped[str] = mapped_column(String(255), nullable=False)
    incident_description: Mapped[str] = mapped_column(Text, nullable=False)
    deviation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    batch_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    product_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    equipment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    incident_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    detection_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    severity: Mapped[SeverityEnum] = mapped_column(
        SAEnum(SeverityEnum, name="severity_enum", native_enum=False),
        nullable=False,
        default=SeverityEnum.MEDIUM,
    )
    immediate_action_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Investigation context
    expected_condition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actual_condition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observed_impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    affected_process: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    initial_observations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Workflow & lifecycle
    investigation_status: Mapped[InvestigationStatusEnum] = mapped_column(
        SAEnum(InvestigationStatusEnum, name="investigation_status_enum", native_enum=False),
        nullable=False,
        default=InvestigationStatusEnum.OPEN,
        index=True,
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
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships (Restrictive ondelete to protect quality records from silent deletion)
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="investigation",
    )
    rca_analyses: Mapped[List["RCAAnalysis"]] = relationship(
        "RCAAnalysis",
        back_populates="investigation",
    )
    evidence_records: Mapped[List["Evidence"]] = relationship(
        "Evidence",
        back_populates="investigation",
    )
    capa_actions: Mapped[List["CapaAction"]] = relationship(
        "CapaAction",
        back_populates="investigation",
    )
    activities: Mapped[List["InvestigationActivity"]] = relationship(
        "InvestigationActivity",
        back_populates="investigation",
    )

    __table_args__ = (
        Index("ix_investigations_dept_status", "department", "investigation_status"),
        Index("ix_investigations_created_at", "created_at"),
    )
