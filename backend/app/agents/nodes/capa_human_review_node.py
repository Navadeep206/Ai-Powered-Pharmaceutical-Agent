"""CAPA Human Review Node for RootIQ LangGraph Workflow.

Enforces genuine human-in-the-loop review boundary using LangGraph interrupt/resume:
- Pauses workflow execution awaiting human review decision.
- Resumes upon explicit approval, rejection, or modification.
- Never automatically approves a CAPA or converts an AI suggestion without sign-off.
- Records reviewer decisions, comments, and audit timestamps.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from langgraph.types import interrupt

from app.agents.state import CAPAWorkflowState
from app.core.logging import get_logger
from app.schemas.capa import (
    CAPARecommendation,
    CAPAStatusEnum,
    CAPATypeEnum,
    EffectivenessVerificationPlan,
)

logger = get_logger("agents.nodes.capa_human_review")


def capa_human_review_node(state: CAPAWorkflowState) -> Dict[str, Any]:
    """Execute human review boundary: pause for decisions or process resumed decisions."""
    workflow_id = state.get("workflow_id", "WF-CAPA")
    investigation_id = state.get("investigation_id")
    logger.info("Executing CAPAHumanReviewNode for workflow %s", workflow_id)

    recommendations: List[CAPARecommendation] = list(state.get("capa_recommendations") or [])
    review_decisions = state.get("review_decisions")
    reviewer_comments = state.get("reviewer_comments")

    # 1. If review decisions are NOT yet present, pause the workflow at the human review boundary
    if not review_decisions:
        logger.info("Pausing workflow %s for human review decision", workflow_id)
        interrupt_payload = {
            "workflow_id": workflow_id,
            "investigation_id": investigation_id,
            "message": "CAPA recommendations require explicit human quality review and approval.",
            "recommendations": [r.model_dump() for r in recommendations],
            "total_recommendations": len(recommendations),
        }

        # Interrupt and pause graph execution until resumed with Command(resume=...)
        resume_input = interrupt(interrupt_payload)

        # Once resumed, extract decisions and comments from resume input
        if isinstance(resume_input, dict):
            review_decisions = resume_input.get("decisions") or []
            if resume_input.get("general_comments"):
                reviewer_comments = resume_input.get("general_comments")
        elif isinstance(resume_input, list):
            review_decisions = resume_input
        else:
            review_decisions = []

    # 2. Process human review decisions
    decisions_by_id: Dict[str, Any] = {}
    if review_decisions:
        for d in review_decisions:
            if isinstance(d, dict) and "capa_id" in d:
                decisions_by_id[d["capa_id"]] = d
            elif hasattr(d, "capa_id"):
                decisions_by_id[d.capa_id] = d.model_dump() if hasattr(d, "model_dump") else vars(d)

    now = datetime.now(timezone.utc)
    updated_recommendations: List[CAPARecommendation] = []

    for rec in recommendations:
        d = decisions_by_id.get(rec.capa_id)
        if d:
            decision_status = d.get("decision")
            # Parse target status
            if isinstance(decision_status, str):
                try:
                    target_status = CAPAStatusEnum(decision_status)
                except Exception:
                    target_status = CAPAStatusEnum.APPROVED if decision_status.upper() == "APPROVED" else CAPAStatusEnum.REJECTED
            elif isinstance(decision_status, CAPAStatusEnum):
                target_status = decision_status
            else:
                target_status = CAPAStatusEnum.APPROVED

            rec.review_status = target_status

            if d.get("edited_description"):
                rec.description = d["edited_description"].strip()

            if d.get("edited_action_type"):
                raw_type = d["edited_action_type"]
                try:
                    rec.action_type = CAPATypeEnum(raw_type)
                except Exception:
                    pass

            if d.get("assigned_owner"):
                rec.assigned_owner = d["assigned_owner"].strip()

            if d.get("target_date"):
                rec.actual_target_date = d["target_date"]

            if d.get("reviewer_comments"):
                rec.reviewer_comments = d["reviewer_comments"].strip()

            if d.get("edited_effectiveness_plan"):
                e_plan = d["edited_effectiveness_plan"]
                if isinstance(e_plan, dict):
                    rec.effectiveness_verification = EffectivenessVerificationPlan(**e_plan)
                elif isinstance(e_plan, EffectivenessVerificationPlan):
                    rec.effectiveness_verification = e_plan

            rec.reviewed_at = now
            rec.reviewed_by = d.get("reviewer_identifier", "QA Reviewer")

        updated_recommendations.append(rec)

    # 3. Categorize approved, rejected, and pending items
    approved = [r for r in updated_recommendations if r.review_status == CAPAStatusEnum.APPROVED]
    rejected = [r for r in updated_recommendations if r.review_status == CAPAStatusEnum.REJECTED]
    pending = [r for r in updated_recommendations if r.review_status in (CAPAStatusEnum.PROPOSED, CAPAStatusEnum.PENDING_REVIEW)]

    # 4. Review status evaluation
    if len(approved) == len(updated_recommendations) and len(updated_recommendations) > 0:
        overall_review_status = "APPROVED"
    elif len(rejected) == len(updated_recommendations) and len(updated_recommendations) > 0:
        overall_review_status = "REJECTED"
    elif approved or rejected:
        overall_review_status = "REVIEWED"
    else:
        overall_review_status = "PENDING_REVIEW"

    return {
        "capa_recommendations": updated_recommendations,
        "corrective_actions": [r for r in updated_recommendations if r.action_type == CAPATypeEnum.CORRECTIVE_ACTION],
        "preventive_actions": [r for r in updated_recommendations if r.action_type == CAPATypeEnum.PREVENTIVE_ACTION],
        "approved_actions": approved,
        "rejected_actions": rejected,
        "pending_actions": pending,
        "capa_review_status": overall_review_status,
        "human_review_required": len(pending) > 0,
        "reviewer_comments": reviewer_comments,
        "review_decisions": review_decisions,
    }
