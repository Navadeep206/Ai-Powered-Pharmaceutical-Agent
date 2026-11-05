"""Corrective and Preventive Actions (CAPA) Business Service for RootIQ.

Handles validation, lifecycle state transitions, effectiveness verification rules,
and audit controls under FDA 21 CFR Part 211 and ICH Q10 pharmaceutical quality systems.
"""

import uuid
from datetime import date, datetime, timezone
from typing import List, Optional, Set, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.exceptions import (
    InvalidCAPADataError,
    InvalidCAPAStatusError,
    InvalidCAPAStatusTransitionError,
)
from app.core.logging import get_logger
from app.models.capa import CapaAction
from app.models.rca import FishboneCause
from app.repositories.activity_repository import activity_repository
from app.repositories.capa_repository import capa_repository
from app.repositories.investigation_repository import investigation_repository
from app.schemas.capa import (
    CAPACreate,
    CAPARecommendation,
    CAPAResponse,
    CAPAReviewItemDecision,
    CAPAReviewRequest,
    CAPAStatusEnum,
    CAPAStatusUpdate,
    CAPATypeEnum,
    CAPAWorkflowResult,
)

logger = get_logger("services.capa")

# Permitted CAPA lifecycle transitions
ALLOWED_CAPA_TRANSITIONS: Set[Tuple[CAPAStatusEnum, CAPAStatusEnum]] = {
    (CAPAStatusEnum.DRAFT, CAPAStatusEnum.PROPOSED),
    (CAPAStatusEnum.PROPOSED, CAPAStatusEnum.PENDING_REVIEW),
    (CAPAStatusEnum.PROPOSED, CAPAStatusEnum.APPROVED),
    (CAPAStatusEnum.PROPOSED, CAPAStatusEnum.REJECTED),
    (CAPAStatusEnum.PROPOSED, CAPAStatusEnum.DRAFT),
    (CAPAStatusEnum.PENDING_REVIEW, CAPAStatusEnum.APPROVED),
    (CAPAStatusEnum.PENDING_REVIEW, CAPAStatusEnum.REJECTED),
    (CAPAStatusEnum.PENDING_REVIEW, CAPAStatusEnum.PROPOSED),
    (CAPAStatusEnum.APPROVED, CAPAStatusEnum.IN_PROGRESS),
    (CAPAStatusEnum.IN_PROGRESS, CAPAStatusEnum.COMPLETED),
    (CAPAStatusEnum.COMPLETED, CAPAStatusEnum.CLOSED),
    (CAPAStatusEnum.COMPLETED, CAPAStatusEnum.IN_PROGRESS),  # Re-opened if verification fails
    (CAPAStatusEnum.REJECTED, CAPAStatusEnum.DRAFT),
    (CAPAStatusEnum.REJECTED, CAPAStatusEnum.PROPOSED),
}


class CAPAService:
    """Service providing CAPA validation, lifecycle gates, and audit preparation."""

    def generate_capa_id(self) -> str:
        """Generate unique CAPA identifier: CAPA-XXXXX."""
        suffix = uuid.uuid4().hex[:6].upper()
        return f"CAPA-{suffix}"

    def validate_capa_status_transition(
        self,
        current_status: CAPAStatusEnum,
        new_status: CAPAStatusEnum,
    ) -> None:
        """Enforce strict ICH Q10 CAPA progression gates."""
        if current_status == new_status:
            return

        if (current_status, new_status) not in ALLOWED_CAPA_TRANSITIONS:
            raise InvalidCAPAStatusTransitionError(
                f"Cannot transition CAPA from '{current_status.value}' to '{new_status.value}'. Must follow formal approval workflow (Draft -> Proposed -> Approved -> In Progress -> Completed -> Closed)."
            )

    def validate_capa_creation(self, payload: CAPACreate) -> CAPACreate:
        """Validate newly submitted CAPA proposal and enforce approval gates."""
        description = payload.description.strip() if payload.description else ""
        if len(description) < 10:
            raise InvalidCAPADataError(
                "CAPA description must provide at least 10 characters detailing remediation or preventive steps."
            )

        action_owner = payload.action_owner.strip() if payload.action_owner else ""
        if len(action_owner) < 2:
            raise InvalidCAPADataError("Action owner must identify a valid responsible role or individual.")

        verification_method = (
            payload.effectiveness_verification_method.strip()
            if payload.effectiveness_verification_method
            else ""
        )
        if len(verification_method) < 10:
            raise InvalidCAPADataError(
                "Effectiveness verification method must specify measurable criteria to verify non-recurrence (minimum 10 characters)."
            )

        if payload.action_type not in CAPATypeEnum:
            raise InvalidCAPADataError(
                f"Invalid action type '{payload.action_type}'. Must be 'Corrective Action' or 'Preventive Action'."
            )

        # GxP Gate: Newly proposed actions cannot be submitted directly as Approved or Completed
        status = payload.status or CAPAStatusEnum.DRAFT
        if status in (CAPAStatusEnum.APPROVED, CAPAStatusEnum.COMPLETED, CAPAStatusEnum.CLOSED):
            raise InvalidCAPAStatusError(
                f"New CAPA actions cannot be initiated in '{status.value}' status. Initial proposals must begin in 'Draft' or 'Proposed' status pending QA review."
            )

        root_cause_ref = (
            payload.related_root_cause_reference.strip()
            if payload.related_root_cause_reference
            else None
        )

        return CAPACreate(
            action_type=payload.action_type,
            description=description,
            action_owner=action_owner,
            target_date=payload.target_date,
            effectiveness_verification_method=verification_method,
            status=status,
            related_root_cause_reference=root_cause_ref,
        )

    def prepare_capa_response(
        self,
        investigation_id: str,
        validated_data: CAPACreate,
        action_id: Optional[str] = None,
    ) -> CAPAResponse:
        """Construct full CAPAResponse object."""
        now = datetime.now(timezone.utc)
        return CAPAResponse(
            action_id=action_id or self.generate_capa_id(),
            investigation_id=investigation_id,
            action_type=validated_data.action_type,
            description=validated_data.description,
            action_owner=validated_data.action_owner,
            target_date=validated_data.target_date,
            effectiveness_verification_method=validated_data.effectiveness_verification_method,
            status=validated_data.status or CAPAStatusEnum.DRAFT,
            related_root_cause_reference=validated_data.related_root_cause_reference,
            created_at=now,
            updated_at=now,
        )


    def to_capa_response(self, investigation_number: str, capa: CapaAction) -> CAPAResponse:
        """Convert ORM CapaAction model to CAPAResponse schema."""
        return CAPAResponse(
            action_id=str(capa.id),
            investigation_id=investigation_number,
            action_type=capa.action_type,
            description=capa.description,
            action_owner=capa.action_owner,
            target_date=capa.target_date,
            effectiveness_verification_method=capa.effectiveness_verification,
            status=capa.action_status,
            related_root_cause_reference=str(capa.related_root_cause_id) if capa.related_root_cause_id else None,
            created_at=capa.created_at,
            updated_at=capa.updated_at,
        )

    def create_capa(
        self,
        db: Session,
        investigation_id: str,
        payload: CAPACreate,
    ) -> CAPAResponse:
        """Validate, persist in PostgreSQL, record activity, and return CAPA response."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        validated = self.validate_capa_creation(payload)

        # Resolve root cause ID if reference is provided
        root_cause_id = None
        if validated.related_root_cause_reference:
            try:
                candidate_uuid = uuid.UUID(validated.related_root_cause_reference)
                # Verify that this cause exists in DB
                cause_exists = db.get(FishboneCause, candidate_uuid)
                if cause_exists:
                    root_cause_id = candidate_uuid
            except (ValueError, AttributeError):
                # Not a raw UUID string, could be a label or non-UUID identifier
                pass

        capa_data = {
            "investigation_id": inv.id,
            "related_root_cause_id": root_cause_id,
            "action_type": validated.action_type,
            "description": validated.description,
            "action_owner": validated.action_owner,
            "target_date": validated.target_date,
            "effectiveness_verification": validated.effectiveness_verification_method,
            "action_status": validated.status or CAPAStatusEnum.DRAFT,
        }

        try:
            capa = capa_repository.create(db, capa_data)
            activity_repository.create(
                db,
                {
                    "investigation_id": inv.id,
                    "activity_type": "CAPA_ACTION_CREATED",
                    "description": f"CAPA action ({validated.action_type.value}) created: {validated.description[:80]}",
                    "actor_identifier": "System",
                    "activity_metadata": {
                        "action_type": validated.action_type.value,
                        "owner": validated.action_owner,
                        "target_date": validated.target_date.isoformat(),
                    },
                },
            )
            db.commit()
            db.refresh(capa)
            return self.to_capa_response(inv.investigation_number, capa)
        except Exception:
            db.rollback()
            raise

    def list_capa(
        self,
        db: Session,
        investigation_id: str,
    ) -> List[CAPAResponse]:
        """Fetch all CAPA actions linked to an investigation."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        items = capa_repository.list_by_investigation(db, inv.id)
        return [self.to_capa_response(inv.investigation_number, item) for item in items]

    def update_capa_status(
        self,
        db: Session,
        investigation_id: str,
        capa_id: str,
        payload: CAPAStatusUpdate,
    ) -> CAPAResponse:
        """Apply lifecycle status change with GxP state machine verification."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        capa = capa_repository.get_by_id(db, capa_id)
        if not capa or capa.investigation_id != inv.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"CAPA action '{capa_id}' not found for investigation '{investigation_id}'.",
            )

        self.validate_capa_status_transition(capa.action_status, payload.status)

        update_data = {"action_status": payload.status}
        if payload.status in (CAPAStatusEnum.COMPLETED, CAPAStatusEnum.CLOSED) and not capa.completed_at:
            update_data["completed_at"] = datetime.now(timezone.utc)

        try:
            updated_capa = capa_repository.update(db, capa, update_data)
            activity_repository.create(
                db,
                {
                    "investigation_id": inv.id,
                    "activity_type": "CAPA_STATUS_CHANGED",
                    "description": f"CAPA {capa.id} transitioned to '{payload.status.value}'.",
                    "actor_identifier": "System",
                    "activity_metadata": {
                        "previous_status": capa.action_status.value,
                        "new_status": payload.status.value,
                        "notes": payload.notes,
                    },
                },
            )
            db.commit()
            db.refresh(updated_capa)
            return self.to_capa_response(inv.investigation_number, updated_capa)
        except Exception:
            db.rollback()
            raise

    def persist_capa_recommendations(
        self,
        db: Session,
        investigation_id: str,
        recommendations: List[CAPARecommendation],
    ) -> List[CapaAction]:
        """Atomically persist proposed CAPA recommendations to PostgreSQL without overwriting approved actions."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        existing_actions = capa_repository.list_by_investigation(db, inv.id)
        existing_by_desc = {a.description.strip().lower(): a for a in existing_actions}

        persisted: List[CapaAction] = []
        try:
            for rec in recommendations:
                desc_key = rec.description.strip().lower()
                existing = existing_by_desc.get(desc_key)

                # If existing is already approved or completed, protect it from overwrite
                if existing:
                    if existing.action_status in (
                        CAPAStatusEnum.APPROVED,
                        CAPAStatusEnum.IN_PROGRESS,
                        CAPAStatusEnum.COMPLETED,
                        CAPAStatusEnum.CLOSED,
                    ):
                        logger.info("Preserving existing approved/completed CAPA %s", existing.id)
                        persisted.append(existing)
                        continue
                    else:
                        existing.action_owner = rec.assigned_owner or rec.suggested_owner_role
                        if rec.actual_target_date:
                            existing.target_date = rec.actual_target_date
                        existing.action_status = rec.review_status
                        db.flush()
                        persisted.append(existing)
                        continue

                # Target date calculation
                target_d = rec.actual_target_date
                if not target_d:
                    from datetime import timedelta
                    target_d = date.today() + timedelta(days=30)

                eff = rec.effectiveness_verification
                eff_text = (
                    f"Method: {eff.verification_method} | "
                    f"Target: {eff.measurable_outcome} | "
                    f"Evidence: {eff.evidence_required} | "
                    f"Verifier: {eff.suggested_verifier_role} | "
                    f"Timeframe: {eff.verification_timeframe} | "
                    f"Failure Criteria: {eff.failure_criteria}"
                )

                root_cause_uuid = None
                if rec.related_root_cause_id:
                    try:
                        cand_uuid = uuid.UUID(rec.related_root_cause_id)
                        if db.get(FishboneCause, cand_uuid):
                            root_cause_uuid = cand_uuid
                    except Exception:
                        pass

                capa_entity = CapaAction(
                    investigation_id=inv.id,
                    related_root_cause_id=root_cause_uuid,
                    action_type=rec.action_type,
                    description=rec.description.strip(),
                    action_owner=rec.assigned_owner or rec.suggested_owner_role,
                    target_date=target_d,
                    effectiveness_verification=eff_text,
                    action_status=rec.review_status or CAPAStatusEnum.PROPOSED,
                )
                db.add(capa_entity)
                db.flush()
                persisted.append(capa_entity)
                existing_by_desc[desc_key] = capa_entity

            activity_repository.create(
                db,
                {
                    "investigation_id": inv.id,
                    "activity_type": "AI_CAPA_PROPOSED",
                    "description": f"Persisted {len(persisted)} reviewable CAPA suggestions for {inv.investigation_number}.",
                    "actor_identifier": "RootIQ AI Engine",
                    "activity_metadata": {
                        "count": len(persisted),
                    },
                },
            )

            db.commit()
            for p in persisted:
                db.refresh(p)
            return persisted
        except Exception:
            db.rollback()
            raise

    def apply_capa_review_decisions(
        self,
        db: Session,
        investigation_id: str,
        decisions: List[CAPAReviewItemDecision],
        reviewer_comments: Optional[str] = None,
    ) -> List[CapaAction]:
        """Apply human QA review decisions (approval, rejection, owner/target date edits) in PostgreSQL."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        existing_actions = capa_repository.list_by_investigation(db, inv.id)
        updated_actions: List[CapaAction] = []

        try:
            for d in decisions:
                target_action = None
                try:
                    cand_uuid = uuid.UUID(d.capa_id)
                    target_action = next((a for a in existing_actions if a.id == cand_uuid), None)
                except Exception:
                    pass

                if not target_action:
                    for a in existing_actions:
                        if d.edited_description and d.edited_description[:30].lower() in a.description.lower():
                            target_action = a
                            break
                    if not target_action and existing_actions:
                        if "01" in d.capa_id and len(existing_actions) >= 1:
                            target_action = existing_actions[0]
                        elif "02" in d.capa_id and len(existing_actions) >= 2:
                            target_action = existing_actions[1]

                if target_action:
                    # Prevent changing status of closed/completed actions
                    if target_action.action_status in (CAPAStatusEnum.COMPLETED, CAPAStatusEnum.CLOSED):
                        if d.decision not in (CAPAStatusEnum.COMPLETED, CAPAStatusEnum.CLOSED):
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Cannot alter status of closed CAPA action '{target_action.id}'.",
                            )

                    target_action.action_status = d.decision
                    if d.edited_description:
                        target_action.description = d.edited_description.strip()
                    if d.edited_action_type:
                        target_action.action_type = d.edited_action_type
                    if d.assigned_owner:
                        target_action.action_owner = d.assigned_owner.strip()
                    if d.target_date:
                        target_action.target_date = d.target_date
                    if d.edited_effectiveness_plan:
                        eff = d.edited_effectiveness_plan
                        target_action.effectiveness_verification = (
                            f"Method: {eff.verification_method} | "
                            f"Target: {eff.measurable_outcome} | "
                            f"Evidence: {eff.evidence_required} | "
                            f"Verifier: {eff.suggested_verifier_role} | "
                            f"Timeframe: {eff.verification_timeframe} | "
                            f"Failure Criteria: {eff.failure_criteria}"
                        )
                    db.flush()
                    updated_actions.append(target_action)

            activity_repository.create(
                db,
                {
                    "investigation_id": inv.id,
                    "activity_type": "CAPA_REVIEW_DECISION",
                    "description": f"Human review decision applied for {len(updated_actions)} CAPA actions.",
                    "actor_identifier": decisions[0].reviewer_identifier if decisions else "QA Reviewer",
                    "activity_metadata": {
                        "reviewer_comments": reviewer_comments,
                        "updated_count": len(updated_actions),
                    },
                },
            )

            db.commit()
            for a in updated_actions:
                db.refresh(a)
            return updated_actions
        except Exception:
            db.rollback()
            raise

    def generate_capa(
        self,
        db: Session,
        investigation_id: str,
        problem_statement: Optional[str] = None,
        persist: bool = True,
    ) -> CAPAWorkflowResult:
        """Execute AI-assisted CAPA recommendations workflow for an investigation."""
        inv = investigation_repository.get_by_id(db, investigation_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation '{investigation_id}' not found.",
            )

        from app.agents.graph import run_capa_generation_workflow

        title = getattr(inv, "incident_title", getattr(inv, "title", "Deviation Excursion"))
        desc = getattr(inv, "incident_description", getattr(inv, "description", ""))
        equip = getattr(inv, "equipment", getattr(inv, "manufacturing_line", ""))

        stmt = problem_statement or f"{title}: {desc[:150]}"
        context = {
            "title": title,
            "description": desc,
            "batch_number": inv.batch_number,
            "equipment_id": equip,
        }

        # Check if existing RCA exists to pull potential root causes
        from app.repositories.rca_repository import rca_repository
        from app.schemas.rca import PotentialRootCause

        rca_study = rca_repository.get_latest_by_investigation(db, inv.id)
        causes: List[PotentialRootCause] = []
        if rca_study and rca_study.five_whys:
            terminal_why = next((w for w in rca_study.five_whys if w.is_root_cause), rca_study.five_whys[-1])
            causes.append(
                PotentialRootCause(
                    cause_id="PRC-01",
                    cause_description=terminal_why.answer,
                    cause_category="Machine / Method",
                    source_method="Five Whys",
                    supporting_evidence=terminal_why.supporting_evidence_references or [],
                    confidence=0.9,
                    rationale="Designated from confirmed/draft terminal Why step.",
                )
            )

        return run_capa_generation_workflow(
            problem_statement=stmt,
            incident_context=context,
            potential_root_causes=causes,
            investigation_id=str(inv.id),
            persist=persist,
            db=db,
        )


# Singleton service instance
capa_service = CAPAService()
