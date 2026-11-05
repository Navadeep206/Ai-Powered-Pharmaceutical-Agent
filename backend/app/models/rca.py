"""SQLAlchemy ORM models for Root Cause Analysis (5-Whys and Ishikawa 6M Fishbone)."""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base
from app.schemas.rca import CauseVerificationStatusEnum, FishboneCategoryEnum


class RCAAnalysis(Base):
    """Container entity representing an RCA study associated with an investigation."""

    __tablename__ = "rca_analyses"

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
    )
    analysis_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="COMBINED",
        comment="Methodology: '5_WHYS', 'FISHBONE', or 'COMBINED'",
    )
    analysis_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Draft",
        comment="Status: 'Draft', 'Under Review', 'Verified', or 'Approved'",
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Executive summary of systemic findings and causal breakdown",
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
        back_populates="rca_analyses",
    )
    five_whys: Mapped[List["FiveWhy"]] = relationship(
        "FiveWhy",
        back_populates="rca_analysis",
        cascade="all, delete-orphan",
        order_by="FiveWhy.why_number",
    )
    fishbone_causes: Mapped[List["FishboneCause"]] = relationship(
        "FishboneCause",
        back_populates="rca_analysis",
        cascade="all, delete-orphan",
    )


class FiveWhy(Base):
    """Step in a 5-Whys causal chain."""

    __tablename__ = "five_whys"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    rca_analysis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("rca_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    why_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequential depth index 1 through 5",
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence_references: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="List of attached evidence citations or document keys",
    )
    is_root_cause: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Denotes the designated root cause level",
    )
    review_status: Mapped[CauseVerificationStatusEnum] = mapped_column(
        SAEnum(CauseVerificationStatusEnum, name="five_whys_status_enum", native_enum=False),
        nullable=False,
        default=CauseVerificationStatusEnum.AI_SUGGESTION,
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

    # Relationship
    rca_analysis: Mapped["RCAAnalysis"] = relationship(
        "RCAAnalysis",
        back_populates="five_whys",
    )

    __table_args__ = (
        CheckConstraint("why_number >= 1 AND why_number <= 5", name="ck_five_whys_range"),
        UniqueConstraint("rca_analysis_id", "why_number", name="uq_rca_analysis_why_number"),
    )


class FishboneCause(Base):
    """Potential or verified causal factor mapped to the 6M Ishikawa diagram."""

    __tablename__ = "fishbone_causes"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    rca_analysis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("rca_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[FishboneCategoryEnum] = mapped_column(
        SAEnum(FishboneCategoryEnum, name="fishbone_category_enum", native_enum=False),
        nullable=False,
    )
    cause_description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_references: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Associated evidence IDs validating or disputing this cause",
    )
    cause_origin: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="AI Suggestion",
        comment="'AI Suggestion', 'Investigator Added', or 'Telemetry Inferred'",
    )
    review_status: Mapped[CauseVerificationStatusEnum] = mapped_column(
        SAEnum(CauseVerificationStatusEnum, name="fishbone_cause_status_enum", native_enum=False),
        nullable=False,
        default=CauseVerificationStatusEnum.AI_SUGGESTION,
    )
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Investigator who reviewed and confirmed this cause",
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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
    rca_analysis: Mapped["RCAAnalysis"] = relationship(
        "RCAAnalysis",
        back_populates="fishbone_causes",
    )
    related_capa_actions: Mapped[List["CapaAction"]] = relationship(
        "CapaAction",
        back_populates="related_root_cause",
    )
