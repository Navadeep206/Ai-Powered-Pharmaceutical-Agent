"""SQLAlchemy 2.0 Repository for Root Cause Analysis (RCA) persistence."""

import uuid
from typing import List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.models.rca import FishboneCause, FiveWhy, RCAAnalysis


class RCARepository:
    """Encapsulates transactional persistence for RCA studies, 5-Whys, and Ishikawa 6M causes."""

    def save_rca_study(
        self,
        db: Session,
        investigation_id: uuid.UUID,
        analysis_method: str,
        summary: Optional[str],
        five_whys_items: List[dict],
        fishbone_items: List[dict],
        analysis_status: str = "Draft",
    ) -> RCAAnalysis:
        """Atomically persist an RCA analysis with its associated 5-Whys chain and Ishikawa causes."""
        # Check if an active analysis already exists for this investigation, or create new
        stmt = (
            select(RCAAnalysis)
            .where(RCAAnalysis.investigation_id == investigation_id)
            .order_by(RCAAnalysis.created_at.desc())
            .options(
                selectinload(RCAAnalysis.five_whys),
                selectinload(RCAAnalysis.fishbone_causes),
            )
        )
        existing_analysis = db.scalars(stmt).first()

        if existing_analysis:
            analysis = existing_analysis
            analysis.analysis_method = analysis_method
            analysis.analysis_status = analysis_status
            if summary is not None:
                analysis.summary = summary

            # Clear existing children to be replaced by the updated chain
            analysis.five_whys.clear()
            analysis.fishbone_causes.clear()
            db.flush()
        else:
            analysis = RCAAnalysis(
                investigation_id=investigation_id,
                analysis_method=analysis_method,
                analysis_status=analysis_status,
                summary=summary,
            )
            db.add(analysis)
            db.flush()

        # Add new 5-Whys levels
        for item in five_whys_items:
            why = FiveWhy(
                rca_analysis_id=analysis.id,
                why_number=item["level"],
                question=item["question"],
                answer=item["answer"],
                supporting_evidence_references=item.get("evidence_references", []),
                is_root_cause=item.get("is_root_cause", False),
                review_status=item.get("status"),
            )
            analysis.five_whys.append(why)

        # Add new Fishbone causes
        for item in fishbone_items:
            cause = FishboneCause(
                rca_analysis_id=analysis.id,
                category=item["category"],
                cause_description=item["cause_description"],
                evidence_references=item.get("evidence_references", []),
                cause_origin="Investigator Added",
                review_status=item.get("status"),
            )
            analysis.fishbone_causes.append(cause)

        db.flush()
        return analysis

    def get_latest_by_investigation(
        self,
        db: Session,
        investigation_id: Union[uuid.UUID, str],
    ) -> Optional[RCAAnalysis]:
        """Fetch the most recent RCA analysis for an investigation, eagerly loading causal children."""
        if not isinstance(investigation_id, uuid.UUID):
            try:
                investigation_id = uuid.UUID(str(investigation_id))
            except (ValueError, AttributeError):
                return None

        stmt = (
            select(RCAAnalysis)
            .where(RCAAnalysis.investigation_id == investigation_id)
            .order_by(RCAAnalysis.created_at.desc())
            .options(
                selectinload(RCAAnalysis.five_whys),
                selectinload(RCAAnalysis.fishbone_causes),
            )
        )
        return db.scalars(stmt).first()

    def list_by_investigation(
        self,
        db: Session,
        investigation_id: Union[uuid.UUID, str],
    ) -> List[RCAAnalysis]:
        """Fetch all RCA analyses associated with an investigation."""
        if not isinstance(investigation_id, uuid.UUID):
            try:
                investigation_id = uuid.UUID(str(investigation_id))
            except (ValueError, AttributeError):
                return []

        stmt = (
            select(RCAAnalysis)
            .where(RCAAnalysis.investigation_id == investigation_id)
            .order_by(RCAAnalysis.created_at.desc())
            .options(
                selectinload(RCAAnalysis.five_whys),
                selectinload(RCAAnalysis.fishbone_causes),
            )
        )
        return list(db.scalars(stmt).all())


# Singleton instance
rca_repository = RCARepository()
