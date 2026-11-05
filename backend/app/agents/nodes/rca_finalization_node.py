"""RCA Finalization Node for RootIQ LangGraph Workflow.

Consolidates reasoning outputs into standardized RCAWorkflowResult,
enforces GxP human-in-the-loop review boundaries, and coordinates
transactional persistence to PostgreSQL.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agents.state import RCAWorkflowState
from app.core.logging import get_logger
from app.schemas.rca import (
    ContributingFactor,
    EvidenceAssessment,
    FishboneCause,
    FiveWhysLevel,
    PotentialRootCause,
    RCAWorkflowResult,
)

logger = get_logger("agents.nodes.rca_finalization")


def rca_finalization_node(state: RCAWorkflowState) -> Dict[str, Any]:
    """Assemble final reviewable RCAWorkflowResult contract."""
    workflow_id = state.get("workflow_id", "WF-RCA")
    investigation_id = state.get("investigation_id")
    logger.info("Executing RCAFinalizationNode for workflow %s", workflow_id)

    problem_statement = state.get("problem_statement") or "Observed manufacturing process deviation."
    five_whys_analysis: List[FiveWhysLevel] = list(state.get("five_whys_analysis") or [])
    fishbone_analysis: List[FishboneCause] = list(state.get("fishbone_analysis") or [])
    supporting_evidence: List[EvidenceAssessment] = list(state.get("supporting_evidence") or [])
    contradictory_evidence: List[EvidenceAssessment] = list(state.get("contradictory_evidence") or [])
    all_evidence = supporting_evidence + contradictory_evidence

    potential_root_causes: List[PotentialRootCause] = list(state.get("potential_root_causes") or [])
    contributing_factors: List[ContributingFactor] = list(state.get("contributing_factors") or [])
    missing_evidence: List[str] = list(state.get("missing_evidence") or [])
    investigator_questions: List[str] = list(state.get("investigator_questions") or [])
    rca_warnings: List[str] = list(state.get("rca_warnings") or [])

    # Lifecycle status
    is_failed = len(five_whys_analysis) == 0 and len(fishbone_analysis) == 0 and len(potential_root_causes) == 0
    final_rca_status = "Failed" if is_failed else "Needs Review"

    persisted_in_db = bool(state.get("persisted_in_db", False))
    rca_analysis_id = state.get("rca_analysis_id")

    # Assemble result
    result = RCAWorkflowResult(
        workflow_id=workflow_id,
        investigation_id=investigation_id,
        problem_statement=problem_statement,
        five_whys_analysis=five_whys_analysis,
        fishbone_analysis=fishbone_analysis,
        evidence_assessment=all_evidence,
        potential_root_causes=potential_root_causes,
        contributing_factors=contributing_factors,
        missing_evidence=missing_evidence,
        investigator_questions=investigator_questions,
        rca_warnings=rca_warnings,
        rca_status=final_rca_status,
        human_review_required=True,  # GxP Non-negotiable requirement
        persisted_in_db=persisted_in_db,
        analysis_id=rca_analysis_id,
        updated_at=datetime.now(timezone.utc),
    )

    return {
        "rca_workflow_result": result,
        "rca_status": final_rca_status,
        "human_review_required": True,
        "persisted_in_db": persisted_in_db,
        "rca_analysis_id": rca_analysis_id,
    }

