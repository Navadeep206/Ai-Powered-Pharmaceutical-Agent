"""CAPA Finalization Node for RootIQ LangGraph Workflow.

Consolidates CAPA recommendations, human review decisions, validation errors,
and effectiveness verification plans into a standardized CAPAWorkflowResult.
Enforces GxP audit boundaries and ensures investigations are not automatically closed.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.agents.state import CAPAWorkflowState
from app.core.logging import get_logger
from app.schemas.capa import (
    CAPARecommendation,
    CAPAWorkflowResult,
)
from app.schemas.rca import PotentialRootCause

logger = get_logger("agents.nodes.capa_finalization")


def capa_finalization_node(state: CAPAWorkflowState) -> Dict[str, Any]:
    """Assemble final reviewable CAPAWorkflowResult contract."""
    workflow_id = state.get("workflow_id", "WF-CAPA")
    investigation_id = state.get("investigation_id")
    thread_id = state.get("thread_id", workflow_id)
    logger.info("Executing CAPAFinalizationNode for workflow %s", workflow_id)

    problem_statement = state.get("problem_statement") or "Observed manufacturing process deviation."
    potential_root_causes: List[PotentialRootCause] = list(state.get("potential_root_causes") or [])
    capa_recommendations: List[CAPARecommendation] = list(state.get("capa_recommendations") or [])
    corrective_actions: List[CAPARecommendation] = list(state.get("corrective_actions") or [])
    preventive_actions: List[CAPARecommendation] = list(state.get("preventive_actions") or [])
    approved_actions: List[CAPARecommendation] = list(state.get("approved_actions") or [])
    rejected_actions: List[CAPARecommendation] = list(state.get("rejected_actions") or [])
    pending_actions: List[CAPARecommendation] = list(state.get("pending_actions") or [])

    validation_errors: List[str] = list(state.get("capa_validation_errors") or [])
    capa_warnings: List[str] = list(state.get("capa_warnings") or [])
    capa_gen_status = state.get("capa_generation_status", "COMPLETED")
    capa_review_status = state.get("capa_review_status", "PENDING_REVIEW")
    persisted_capa_ids = list(state.get("persisted_capa_ids") or [])

    # RCA summary string
    rca_summary_parts = [f"Problem: {problem_statement}"]
    if potential_root_causes:
        cause_descs = [f"{c.cause_id}: {c.cause_description}" for c in potential_root_causes]
        rca_summary_parts.append(f"Root Causes: {'; '.join(cause_descs)}")
    rca_summary = " | ".join(rca_summary_parts)

    is_failed = capa_gen_status == "FAILED" and len(capa_recommendations) == 0
    if is_failed:
        completion_status = "FAILED"
    elif pending_actions and not approved_actions and not rejected_actions:
        completion_status = "PAUSED_FOR_HUMAN_REVIEW"
    else:
        completion_status = "COMPLETED"

    human_review_required = len(pending_actions) > 0 or completion_status == "PAUSED_FOR_HUMAN_REVIEW"

    result = CAPAWorkflowResult(
        workflow_id=workflow_id,
        investigation_id=investigation_id,
        thread_id=thread_id,
        rca_summary=rca_summary,
        potential_root_causes=potential_root_causes,
        capa_recommendations=capa_recommendations,
        corrective_actions=corrective_actions,
        preventive_actions=preventive_actions,
        approved_actions=approved_actions,
        rejected_actions=rejected_actions,
        pending_actions=pending_actions,
        validation_errors=validation_errors,
        capa_warnings=capa_warnings,
        capa_generation_status=capa_gen_status,
        capa_review_status=capa_review_status,
        human_review_required=human_review_required,
        workflow_completion_status=completion_status,
        persisted_in_db=len(persisted_capa_ids) > 0,
        persisted_capa_ids=persisted_capa_ids,
        updated_at=datetime.now(timezone.utc),
    )

    return {
        "capa_workflow_result": result,
        "workflow_completion_status": completion_status,
        "human_review_required": human_review_required,
    }
