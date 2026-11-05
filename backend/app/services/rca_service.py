"""Root Cause Analysis (RCA) Business Service for RootIQ.

Enforces strict causal chain integrity, 6M Ishikawa categorization,
and human-in-the-loop verification boundaries adhering to ICH Q9 principles.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.core.exceptions import (
    InvalidFishboneCategoryError,
    InvalidFiveWhysStructureError,
    InvalidRCACauseStatusError,
)
from app.core.logging import get_logger
from app.models.rca import FishboneCause as FishboneCauseModel, FiveWhy, RCAAnalysis
from app.repositories.activity_repository import activity_repository
from app.repositories.evidence_repository import evidence_repository
from app.repositories.investigation_repository import investigation_repository
from app.repositories.rca_repository import rca_repository
from app.schemas.rca import (
    CauseVerificationStatusEnum,
    FishboneCategoryEnum,
    FishboneCause,
    FiveWhysLevel,
    RCAGenerateRequest,
    RCARequest,
    RCAResponse,
    RCAWorkflowResult,
)

logger = get_logger("services.rca")


class RCAService:
    """Service providing RCA validation and causal chain verification."""

    def validate_five_whys(self, five_whys: List[FiveWhysLevel]) -> List[FiveWhysLevel]:
        """Validate sequential ordering, non-empty questions/answers, and root cause designation."""
        if not five_whys:
            return []

        if len(five_whys) > 5:
            raise InvalidFiveWhysStructureError(
                f"5-Whys methodology supports at most 5 sequential levels (provided {len(five_whys)})."
            )

        root_cause_count = 0
        validated_levels: List[FiveWhysLevel] = []

        for idx, item in enumerate(five_whys):
            expected_level = idx + 1
            if item.level != expected_level:
                raise InvalidFiveWhysStructureError(
                    f"5-Whys levels must be strictly sequential without gaps. Expected level {expected_level}, received {item.level}."
                )

            if not item.question or not item.question.strip():
                raise InvalidFiveWhysStructureError(f"Why #{item.level} question cannot be empty.")
            if not item.answer or not item.answer.strip():
                raise InvalidFiveWhysStructureError(f"Why #{item.level} answer cannot be empty.")

            # Rule: AI suggestions cannot be automatically marked as Confirmed Root Cause
            if item.status == CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE and not item.is_root_cause:
                raise InvalidRCACauseStatusError(
                    f"Why #{item.level} has status 'Confirmed Root Cause' but is_root_cause is False."
                )

            if item.is_root_cause:
                root_cause_count += 1
                # Must be the final level in the presented chain
                if idx != len(five_whys) - 1:
                    raise InvalidFiveWhysStructureError(
                        f"Root cause was designated at level {item.level}, but subsequent Why levels ({[x.level for x in five_whys[idx+1:]]}) exist. The primary root cause must be the terminal step of the causal sequence."
                    )

            validated_levels.append(item)

        if root_cause_count > 1:
            raise InvalidFiveWhysStructureError("Only one primary root cause may be designated in a single 5-Whys tree.")

        return validated_levels

    def validate_fishbone_causes(self, causes: List[FishboneCause]) -> List[FishboneCause]:
        """Validate Ishikawa 6M causes, evidence citations, and human confirmation gates."""
        if not causes:
            return []

        validated_causes: List[FishboneCause] = []

        for cause in causes:
            if not cause.cause_id or not cause.cause_id.strip():
                raise InvalidRCACauseStatusError("Each fishbone cause must specify a unique cause_id.")

            if not cause.cause_description or not cause.cause_description.strip():
                raise InvalidRCACauseStatusError(
                    f"Cause '{cause.cause_id}' must provide a non-empty description."
                )

            # Check category validity
            if cause.category not in FishboneCategoryEnum:
                raise InvalidFishboneCategoryError(
                    f"Invalid Fishbone category '{cause.category}'. Must be one of: {[c.value for c in FishboneCategoryEnum]}."
                )

            # Strict GxP Rule: A root cause cannot be confirmed without supporting empirical evidence
            if cause.status == CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE:
                if not cause.evidence_references or len(cause.evidence_references) == 0:
                    raise InvalidRCACauseStatusError(
                        f"Cause '{cause.cause_id}' cannot be marked as 'Confirmed Root Cause' without citing supporting evidence references."
                    )

            validated_causes.append(cause)

        return validated_causes

    def validate_rca_request(self, payload: RCARequest) -> RCARequest:
        """Execute full validation across 5-Whys and Fishbone structures."""
        validated_five_whys = self.validate_five_whys(payload.five_whys)
        validated_fishbone = self.validate_fishbone_causes(payload.fishbone_causes)

        return RCARequest(
            five_whys=validated_five_whys,
            fishbone_causes=validated_fishbone,
            investigator_notes=payload.investigator_notes.strip() if payload.investigator_notes else None,
        )

    def prepare_rca_response(
        self,
        investigation_id: str,
        validated_rca: RCARequest,
    ) -> RCAResponse:
        """Construct full RCAResponse contract."""
        return RCAResponse(
            investigation_id=investigation_id,
            five_whys=validated_rca.five_whys,
            fishbone_causes=validated_rca.fishbone_causes,
            investigator_notes=validated_rca.investigator_notes,
            updated_at=datetime.now(timezone.utc),
        )


    def save_rca_analysis(
        self,
        db: Session,
        investigation_id: str,
        payload: RCARequest,
    ) -> RCAResponse:
        """Validate, persist in transaction, record activity, and return RCA response."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        validated_rca = self.validate_rca_request(payload)

        # Convert schemas to dicts for repository
        five_whys_dicts = [item.model_dump() for item in validated_rca.five_whys]
        fishbone_dicts = [item.model_dump() for item in validated_rca.fishbone_causes]

        try:
            analysis = rca_repository.save_rca_study(
                db=db,
                investigation_id=inv.id,
                analysis_method="COMBINED",
                summary=validated_rca.investigator_notes,
                five_whys_items=five_whys_dicts,
                fishbone_items=fishbone_dicts,
            )
            activity_repository.create(
                db,
                {
                    "investigation_id": inv.id,
                    "activity_type": "RCA_ANALYSIS_SAVED",
                    "description": f"RCA analysis updated for {inv.investigation_number} ({len(five_whys_dicts)} Whys, {len(fishbone_dicts)} Fishbone causes).",
                    "actor_identifier": "System",
                    "activity_metadata": {
                        "whys_count": len(five_whys_dicts),
                        "fishbone_count": len(fishbone_dicts),
                    },
                },
            )
            db.commit()
            db.refresh(analysis)
            return self.to_rca_response(inv.investigation_number, analysis)
        except Exception:
            db.rollback()
            raise

    def get_rca_analysis(
        self,
        db: Session,
        investigation_id: str,
    ) -> RCAResponse:
        """Retrieve the latest RCA analysis for an investigation, or return empty structure if none."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        analysis = rca_repository.get_latest_by_investigation(db, inv.id)
        if not analysis:
            return RCAResponse(
                investigation_id=inv.investigation_number,
                five_whys=[],
                fishbone_causes=[],
                investigator_notes=None,
                updated_at=inv.updated_at,
            )

        return self.to_rca_response(inv.investigation_number, analysis)

    def to_rca_response(self, investigation_number: str, analysis) -> RCAResponse:
        """Convert ORM RCAAnalysis to RCAResponse schema."""
        five_whys = [
            FiveWhysLevel(
                level=w.why_number,
                question=w.question,
                answer=w.answer,
                evidence_references=w.supporting_evidence_references or [],
                is_root_cause=w.is_root_cause,
                status=w.review_status,
            )
            for w in sorted(analysis.five_whys, key=lambda x: x.why_number)
        ]

        fishbone_causes = [
            FishboneCause(
                cause_id=f"CAUSE-{idx+1:02d}",
                category=c.category,
                cause_description=c.cause_description,
                evidence_references=c.evidence_references or [],
                status=c.review_status,
                contributing_factors=[],
            )
            for idx, c in enumerate(analysis.fishbone_causes)
        ]

        return RCAResponse(
            investigation_id=investigation_number,
            five_whys=five_whys,
            fishbone_causes=fishbone_causes,
            investigator_notes=analysis.summary,
            updated_at=analysis.updated_at,
        )

    def persist_rca_workflow_result(
        self,
        db: Session,
        investigation_id: str,
        rca_result: RCAWorkflowResult,
    ) -> RCAAnalysis:
        """Persist RCA workflow findings and evidence into PostgreSQL without overwriting human-confirmed records."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        try:
            # 1. Fetch existing RCAAnalysis or create new
            stmt = (
                select(RCAAnalysis)
                .where(RCAAnalysis.investigation_id == inv.id)
                .order_by(RCAAnalysis.created_at.desc())
                .options(
                    selectinload(RCAAnalysis.five_whys),
                    selectinload(RCAAnalysis.fishbone_causes),
                )
            )
            analysis = db.scalars(stmt).first()

            if not analysis:
                analysis = RCAAnalysis(
                    investigation_id=inv.id,
                    analysis_method="COMBINED",
                    analysis_status="Draft",
                    summary=rca_result.problem_statement,
                )
                db.add(analysis)
                db.flush()
            else:
                if not analysis.summary:
                    analysis.summary = rca_result.problem_statement

            # 2. Update Five Whys without overwriting human confirmed/reviewed
            existing_whys = list(analysis.five_whys)
            human_reviewed_whys = {
                w.why_number: w
                for w in existing_whys
                if w.review_status in (
                    CauseVerificationStatusEnum.HUMAN_REVIEWED,
                    CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE,
                )
            }

            # Retain human reviewed whys
            retained_whys = [w for w in existing_whys if w.why_number in human_reviewed_whys]
            analysis.five_whys.clear()
            for w in retained_whys:
                analysis.five_whys.append(w)

            # Add newly generated AI whys where human whys don't already occupy the level
            for w in rca_result.five_whys_analysis:
                if w.level not in human_reviewed_whys:
                    new_why = FiveWhy(
                        rca_analysis_id=analysis.id,
                        why_number=w.level,
                        question=w.question,
                        answer=w.answer,
                        supporting_evidence_references=w.supporting_evidence_references or w.evidence_references,
                        is_root_cause=w.is_root_cause,
                        review_status=w.status,
                    )
                    analysis.five_whys.append(new_why)

            # 3. Update Fishbone causes without overwriting human confirmed/reviewed
            existing_causes = list(analysis.fishbone_causes)
            human_reviewed_causes = [
                c for c in existing_causes
                if c.review_status in (
                    CauseVerificationStatusEnum.HUMAN_REVIEWED,
                    CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE,
                )
            ]
            analysis.fishbone_causes.clear()
            for c in human_reviewed_causes:
                analysis.fishbone_causes.append(c)

            for c in rca_result.fishbone_analysis:
                cause_model = FishboneCauseModel(
                    rca_analysis_id=analysis.id,
                    category=c.category,
                    cause_description=c.cause_description,
                    evidence_references=c.supporting_evidence_references or c.evidence_references,
                    cause_origin="AI Suggestion",
                    review_status=c.status,
                )
                analysis.fishbone_causes.append(cause_model)

            db.flush()

            # 4. Persist Evidence assessments
            existing_evidences = evidence_repository.list_by_investigation(db, inv.id)
            existing_descriptions = {e.description.strip().lower() for e in existing_evidences}

            for ev in rca_result.evidence_assessment:
                desc_key = ev.evidence_description.strip().lower()
                if desc_key not in existing_descriptions:
                    evidence_repository.create(
                        db,
                        {
                            "investigation_id": inv.id,
                            "evidence_type": ev.evidence_type,
                            "description": ev.evidence_description,
                            "source_reference": ev.source_reference or "Investigation Dossier",
                            "review_status": ev.review_status,
                            "notes": ev.reasoning,
                        },
                    )
                    existing_descriptions.add(desc_key)

            # 5. Record activity
            activity_repository.create(
                db,
                {
                    "investigation_id": inv.id,
                    "activity_type": "AI_RCA_GENERATED",
                    "description": f"AI-assisted RCA reasoning executed for {inv.investigation_number}: {len(rca_result.five_whys_analysis)} Whys, {len(rca_result.fishbone_analysis)} Fishbone causes.",
                    "actor_identifier": "RootIQ AI Engine",
                    "activity_metadata": {
                        "workflow_id": rca_result.workflow_id,
                        "whys_count": len(rca_result.five_whys_analysis),
                        "fishbone_count": len(rca_result.fishbone_analysis),
                        "candidate_root_causes_count": len(rca_result.potential_root_causes),
                    },
                },
            )

            db.commit()
            db.refresh(analysis)
            return analysis
        except Exception:
            db.rollback()
            raise

    def generate_rca(
        self,
        db: Session,
        investigation_id: str,
        payload: Optional[RCAGenerateRequest] = None,
    ) -> RCAWorkflowResult:
        """Execute AI RCA reasoning workflow for an investigation and optionally persist."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        problem_stmt = payload.problem_statement if payload and payload.problem_statement else None
        incident_ctx = dict(payload.incident_context or {}) if payload and payload.incident_context else {}
        facts = list(payload.investigation_facts or []) if payload and payload.investigation_facts else []
        persist = payload.persist if payload is not None else True

        # Enrich context from investigation if missing
        inv_title = getattr(inv, "incident_title", getattr(inv, "title", None))
        inv_desc = getattr(inv, "incident_description", getattr(inv, "description", None))
        inv_equip = getattr(inv, "equipment", getattr(inv, "manufacturing_line", None))

        if "title" not in incident_ctx and inv_title:
            incident_ctx["title"] = inv_title
        if "description" not in incident_ctx and inv_desc:
            incident_ctx["description"] = inv_desc
        if "batch_number" not in incident_ctx and inv.batch_number:
            incident_ctx["batch_number"] = inv.batch_number
        if "equipment_id" not in incident_ctx and inv_equip:
            incident_ctx["equipment_id"] = inv_equip

        from app.agents.graph import run_rca_reasoning_workflow

        result = run_rca_reasoning_workflow(
            problem_statement=problem_stmt,
            incident_context=incident_ctx,
            investigation_facts=facts,
            investigation_id=str(inv.id),
            persist=persist,
            db=db,
        )
        return result


# Singleton service instance
rca_service = RCAService()
