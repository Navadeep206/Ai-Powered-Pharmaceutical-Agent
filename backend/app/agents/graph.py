"""LangGraph Workflow Orchestration for RootIQ Incident Extraction.

Builds and compiles the StateGraph routing input processing, structured extraction,
Pydantic validation, GxP quality assessment, and finalization with MemorySaver checkpointing.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agents.nodes.capa_finalization_node import capa_finalization_node
from app.agents.nodes.capa_generation_node import capa_generation_node
from app.agents.nodes.capa_human_review_node import capa_human_review_node
from app.agents.nodes.capa_validation_node import capa_validation_node
from app.agents.nodes.evidence_analysis_node import evidence_analysis_node
from app.agents.nodes.extraction_node import incident_extraction_node
from app.agents.nodes.finalization_node import finalization_node
from app.agents.nodes.fishbone_node import fishbone_node
from app.agents.nodes.five_whys_node import five_whys_node
from app.agents.nodes.input_node import input_processing_node
from app.agents.nodes.quality_node import quality_assessment_node
from app.agents.nodes.rca_finalization_node import rca_finalization_node
from app.agents.nodes.rca_prep_node import rca_prep_node
from app.agents.nodes.synthesis_node import synthesis_node
from app.agents.nodes.validation_node import structured_validation_node
from app.agents.state import (
    CAPAWorkflowState,
    ExtractionWorkflowState,
    RCAWorkflowState,
)
from app.core.logging import get_logger
from app.schemas.capa import CAPAReviewRequest, CAPAWorkflowResult
from app.schemas.document import NormalizedIncidentIntake
from app.schemas.extraction import ExtractionAnalysisResponse
from app.schemas.rca import RCAWorkflowResult

logger = get_logger("agents.graph")


# -----------------------------------------------------------------------------
# CONDITIONAL ROUTING FUNCTIONS
# -----------------------------------------------------------------------------

def route_after_input(state: ExtractionWorkflowState) -> str:
    """Determine next node after input validation."""
    if state.get("workflow_status") == "FAILED":
        logger.warning("Routing directly to finalization due to input failure.")
        return "finalization_node"
    return "extraction_node"


def route_after_extraction(state: ExtractionWorkflowState) -> str:
    """Determine next node after extraction."""
    if state.get("workflow_status") == "FAILED":
        logger.warning("Routing to finalization due to extraction provider failure.")
        return "finalization_node"
    return "validation_node"


def route_after_validation(state: ExtractionWorkflowState) -> str:
    """Determine next node after validation (handles retry vs quality vs failure)."""
    status = state.get("workflow_status")
    if status == "RETRY":
        logger.info("Routing back to extraction_node for controlled retry.")
        return "extraction_node"
    elif status == "FAILED":
        logger.warning("Routing to finalization due to validation failure.")
        return "finalization_node"
    return "quality_node"


# -----------------------------------------------------------------------------
# GRAPH CONSTRUCTION & COMPILATION
# -----------------------------------------------------------------------------

def build_incident_extraction_graph() -> StateGraph:
    """Assemble the StateGraph structure for incident extraction."""
    builder = StateGraph(ExtractionWorkflowState)

    # 1. Add Nodes
    builder.add_node("input_node", input_processing_node)
    builder.add_node("extraction_node", incident_extraction_node)
    builder.add_node("validation_node", structured_validation_node)
    builder.add_node("quality_node", quality_assessment_node)
    builder.add_node("finalization_node", finalization_node)

    # 2. Add Flow Edges
    builder.add_edge(START, "input_node")

    # Conditional branching from input
    builder.add_conditional_edges(
        "input_node",
        route_after_input,
        {
            "extraction_node": "extraction_node",
            "finalization_node": "finalization_node",
        },
    )

    # Conditional branching from extraction
    builder.add_conditional_edges(
        "extraction_node",
        route_after_extraction,
        {
            "validation_node": "validation_node",
            "finalization_node": "finalization_node",
        },
    )

    # Conditional branching from validation (supports controlled retry)
    builder.add_conditional_edges(
        "validation_node",
        route_after_validation,
        {
            "extraction_node": "extraction_node",
            "quality_node": "quality_node",
            "finalization_node": "finalization_node",
        },
    )

    # Direct progression from quality assessment to finalization
    builder.add_edge("quality_node", "finalization_node")

    # Direct completion
    builder.add_edge("finalization_node", END)

    return builder


# Global development checkpointer
# NOTE: MemorySaver is in-memory and suitable for development testing.
# Future phases will integrate langgraph-checkpoint-postgres when persistent checkpointing is configured.
memory_checkpointer = MemorySaver()

# Compiled application graph
incident_extraction_workflow = build_incident_extraction_graph().compile(
    checkpointer=memory_checkpointer
)


# -----------------------------------------------------------------------------
# HIGH-LEVEL RUNNER FUNCTION
# -----------------------------------------------------------------------------

def run_incident_extraction_workflow(
    normalized_intake: NormalizedIncidentIntake,
    investigation_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> ExtractionAnalysisResponse:
    """Execute the full LangGraph incident extraction workflow and return standardized response."""
    workflow_id = f"WF-EXTRACT-{uuid.uuid4().hex[:10].upper()}"
    active_thread_id = thread_id or workflow_id

    source_type_val = (
        normalized_intake.source_type.value
        if hasattr(normalized_intake.source_type, "value")
        else str(normalized_intake.source_type)
    )

    initial_state: ExtractionWorkflowState = {
        "workflow_id": workflow_id,
        "investigation_id": investigation_id,
        "thread_id": active_thread_id,
        "source_type": source_type_val,
        "source_text": normalized_intake.prepared_incident_text or "",
        "source_filename": normalized_intake.source_filename,
        "source_metadata": {
            "processing_status": normalized_intake.processing_status,
            "page_references": normalized_intake.page_references or [],
        },
        "validation_errors": [],
        "missing_fields": [],
        "critical_gaps": [],
        "ambiguous_fields": [],
        "possible_contradictions": [],
        "investigator_questions": [],
        "completeness_score": 0.0,
        "overall_confidence": 0.0,
        "workflow_status": "PENDING",
        "extraction_status": "PENDING",
        "error_message": None,
        "warnings": list(normalized_intake.processing_warnings or []),
        "retry_count": 0,
        "max_retries": 2,
        "processing_started_at": datetime.now(timezone.utc).isoformat(),
        "processing_completed_at": None,
        "duration_seconds": None,
    }

    config = {"configurable": {"thread_id": active_thread_id}}

    logger.info(
        "Invoking LangGraph incident extraction workflow %s (thread=%s)",
        workflow_id,
        active_thread_id,
    )

    final_state = incident_extraction_workflow.invoke(initial_state, config=config)

    extraction_response: Optional[ExtractionAnalysisResponse] = final_state.get("extraction_response")
    if extraction_response is None:
        # Fallback safeguard in case finalization node did not construct response
        from app.schemas.extraction import OverallExtractionStatus
        from app.services.extraction_service import extraction_service

        empty_data = extraction_service._create_empty_extracted_data(source_type=source_type_val)
        extraction_response = ExtractionAnalysisResponse(
            analysis_id=workflow_id,
            workflow_id=workflow_id,
            workflow_status=final_state.get("workflow_status", "FAILED"),
            duration_seconds=final_state.get("duration_seconds", 0.0),
            intake_method=normalized_intake.source_type,
            extraction_status=OverallExtractionStatus.FAILED,
            extracted_data=empty_data,
            warnings=final_state.get("warnings", []),
            extraction_summary=f"Extraction workflow completed with status {final_state.get('workflow_status')}.",
        )

    return extraction_response


# =============================================================================
# RCA REASONING WORKFLOW GRAPH (FIVE WHYS, FISHBONE, EVIDENCE, SYNTHESIS)
# =============================================================================

def build_rca_reasoning_graph() -> StateGraph:
    """Assemble the StateGraph structure for pharmaceutical RCA reasoning."""
    builder = StateGraph(RCAWorkflowState)

    # 1. Add Reasoning Nodes
    builder.add_node("rca_prep_node", rca_prep_node)
    builder.add_node("five_whys_node", five_whys_node)
    builder.add_node("fishbone_node", fishbone_node)
    builder.add_node("evidence_analysis_node", evidence_analysis_node)
    builder.add_node("synthesis_node", synthesis_node)
    builder.add_node("rca_finalization_node", rca_finalization_node)

    # 2. Add Deterministic Sequence Edges
    builder.add_edge(START, "rca_prep_node")
    builder.add_edge("rca_prep_node", "five_whys_node")
    builder.add_edge("five_whys_node", "fishbone_node")
    builder.add_edge("fishbone_node", "evidence_analysis_node")
    builder.add_edge("evidence_analysis_node", "synthesis_node")
    builder.add_edge("synthesis_node", "rca_finalization_node")
    builder.add_edge("rca_finalization_node", END)

    return builder


# Compiled RCA reasoning workflow with checkpointing
rca_reasoning_workflow = build_rca_reasoning_graph().compile(
    checkpointer=memory_checkpointer
)


def run_rca_reasoning_workflow(
    problem_statement: Optional[str] = None,
    incident_context: Optional[Dict[str, Any]] = None,
    investigation_facts: Optional[List[Dict[str, Any]]] = None,
    investigation_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    persist: bool = False,
    db: Optional[Session] = None,
) -> RCAWorkflowResult:
    """Execute the full LangGraph RCA reasoning workflow and return standardized RCAWorkflowResult."""
    workflow_id = f"WF-RCA-{uuid.uuid4().hex[:10].upper()}"
    active_thread_id = thread_id or workflow_id

    initial_state: RCAWorkflowState = {
        "workflow_id": workflow_id,
        "investigation_id": investigation_id,
        "thread_id": active_thread_id,
        "source_type": "Incident Data",
        "source_text": "",
        "source_filename": None,
        "source_metadata": {},
        "problem_statement": problem_statement or "",
        "incident_context": incident_context or {},
        "investigation_facts": list(investigation_facts or []),
        "evidence_records": [],
        "five_whys_analysis": [],
        "fishbone_analysis": [],
        "potential_root_causes": [],
        "contributing_factors": [],
        "supporting_evidence": [],
        "contradictory_evidence": [],
        "missing_evidence": [],
        "investigator_questions": [],
        "rca_warnings": [],
        "rca_status": "PENDING",
        "human_review_required": True,
        "persisted_in_db": False,
        "rca_analysis_id": None,
        "workflow_status": "PENDING",
        "extraction_status": "PENDING",
        "error_message": None,
        "warnings": [],
        "retry_count": 0,
        "max_retries": 2,
        "processing_started_at": datetime.now(timezone.utc).isoformat(),
        "processing_completed_at": None,
        "duration_seconds": None,
    }

    config = {"configurable": {"thread_id": active_thread_id}}

    logger.info(
        "Invoking LangGraph RCA reasoning workflow %s (thread=%s)",
        workflow_id,
        active_thread_id,
    )

    final_state = rca_reasoning_workflow.invoke(initial_state, config=config)
    rca_result: Optional[RCAWorkflowResult] = final_state.get("rca_workflow_result")

    if rca_result is None:
        # Fallback safeguard in case finalization node was bypassed
        rca_result = RCAWorkflowResult(
            workflow_id=workflow_id,
            investigation_id=investigation_id,
            problem_statement=problem_statement or "Observed manufacturing process deviation.",
            five_whys_analysis=[],
            fishbone_analysis=[],
            evidence_assessment=[],
            potential_root_causes=[],
            contributing_factors=[],
            missing_evidence=[],
            investigator_questions=[],
            rca_warnings=final_state.get("rca_warnings", []),
            rca_status="Failed",
            human_review_required=True,
            persisted_in_db=False,
            analysis_id=None,
            updated_at=datetime.now(timezone.utc),
        )

    # Optional database persistence
    if persist and investigation_id and db is not None:
        from app.services.rca_service import rca_service
        try:
            persisted_analysis = rca_service.persist_rca_workflow_result(
                db=db,
                investigation_id=investigation_id,
                rca_result=rca_result,
            )
            rca_result.persisted_in_db = True
            rca_result.analysis_id = str(persisted_analysis.id)
            logger.info(
                "Persisted RCA workflow result to PostgreSQL (rca_analysis_id=%s)",
                persisted_analysis.id,
            )
        except Exception as err:
            logger.error("Failed to persist RCA workflow result to database: %s", err)
            rca_result.rca_warnings.append(f"Database persistence failed: {err}")

    return rca_result


# =============================================================================
# CAPA GENERATION, VALIDATION & HUMAN REVIEW WORKFLOW
# =============================================================================

def build_capa_workflow() -> StateGraph:
    """Assemble the StateGraph structure for pharmaceutical RCA and CAPA generation and review."""
    builder = StateGraph(CAPAWorkflowState)

    # 1. Add Reasoning, Remediation & Human Review Nodes
    builder.add_node("rca_prep_node", rca_prep_node)
    builder.add_node("five_whys_node", five_whys_node)
    builder.add_node("fishbone_node", fishbone_node)
    builder.add_node("evidence_analysis_node", evidence_analysis_node)
    builder.add_node("synthesis_node", synthesis_node)
    builder.add_node("rca_finalization_node", rca_finalization_node)
    builder.add_node("capa_generation_node", capa_generation_node)
    builder.add_node("capa_validation_node", capa_validation_node)
    builder.add_node("capa_human_review_node", capa_human_review_node)
    builder.add_node("capa_finalization_node", capa_finalization_node)

    # 2. Add Sequential Edges
    builder.add_edge(START, "rca_prep_node")
    builder.add_edge("rca_prep_node", "five_whys_node")
    builder.add_edge("five_whys_node", "fishbone_node")
    builder.add_edge("fishbone_node", "evidence_analysis_node")
    builder.add_edge("evidence_analysis_node", "synthesis_node")
    builder.add_edge("synthesis_node", "rca_finalization_node")
    builder.add_edge("rca_finalization_node", "capa_generation_node")
    builder.add_edge("capa_generation_node", "capa_validation_node")
    builder.add_edge("capa_validation_node", "capa_human_review_node")
    builder.add_edge("capa_human_review_node", "capa_finalization_node")
    builder.add_edge("capa_finalization_node", END)

    return builder


# Compiled CAPA workflow with MemorySaver checkpointing
capa_workflow = build_capa_workflow().compile(checkpointer=memory_checkpointer)


def run_capa_generation_workflow(
    problem_statement: Optional[str] = None,
    incident_context: Optional[Dict[str, Any]] = None,
    investigation_facts: Optional[List[Dict[str, Any]]] = None,
    potential_root_causes: Optional[List[Any]] = None,
    contributing_factors: Optional[List[Any]] = None,
    supporting_evidence: Optional[List[Any]] = None,
    contradictory_evidence: Optional[List[Any]] = None,
    missing_evidence: Optional[List[str]] = None,
    investigation_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    persist: bool = False,
    db: Optional[Session] = None,
) -> CAPAWorkflowResult:
    """Execute RCA and CAPA generation, pausing at the human review boundary with memory checkpointing."""
    workflow_id = f"WF-CAPA-{uuid.uuid4().hex[:10].upper()}"
    active_thread_id = thread_id or workflow_id

    initial_state: CAPAWorkflowState = {
        "workflow_id": workflow_id,
        "investigation_id": investigation_id,
        "thread_id": active_thread_id,
        "source_type": "Incident Data",
        "source_text": "",
        "source_filename": None,
        "source_metadata": {},
        "problem_statement": problem_statement or "",
        "incident_context": incident_context or {},
        "investigation_facts": list(investigation_facts or []),
        "evidence_records": [],
        "five_whys_analysis": [],
        "fishbone_analysis": [],
        "potential_root_causes": list(potential_root_causes or []),
        "contributing_factors": list(contributing_factors or []),
        "supporting_evidence": list(supporting_evidence or []),
        "contradictory_evidence": list(contradictory_evidence or []),
        "missing_evidence": list(missing_evidence or []),
        "investigator_questions": [],
        "rca_warnings": [],
        "rca_status": "PENDING",
        "human_review_required": True,
        "persisted_in_db": False,
        "rca_analysis_id": None,
        "capa_recommendations": [],
        "corrective_actions": [],
        "preventive_actions": [],
        "approved_actions": [],
        "rejected_actions": [],
        "pending_actions": [],
        "capa_validation_errors": [],
        "capa_warnings": [],
        "capa_generation_status": "PENDING",
        "capa_review_status": "PENDING_REVIEW",
        "review_decisions": [],
        "reviewer_comments": None,
        "workflow_completion_status": "PAUSED_FOR_HUMAN_REVIEW",
        "persisted_capa_ids": [],
        "workflow_status": "PENDING",
        "extraction_status": "PENDING",
        "error_message": None,
        "warnings": [],
        "retry_count": 0,
        "max_retries": 2,
        "processing_started_at": datetime.now(timezone.utc).isoformat(),
        "processing_completed_at": None,
        "duration_seconds": None,
    }

    config = {"configurable": {"thread_id": active_thread_id}}

    logger.info("Invoking LangGraph CAPA workflow %s (thread=%s)", workflow_id, active_thread_id)
    final_output = capa_workflow.invoke(initial_state, config=config)

    # Check state snapshot from checkpointer
    state_snap = capa_workflow.get_state(config)
    current_values = state_snap.values if state_snap else final_output

    capa_result: Optional[CAPAWorkflowResult] = current_values.get("capa_workflow_result")
    if capa_result is None:
        recs = current_values.get("capa_recommendations", [])
        cas = current_values.get("corrective_actions", [])
        pas = current_values.get("preventive_actions", [])
        val_errors = current_values.get("capa_validation_errors", [])
        warns = current_values.get("capa_warnings", [])
        causes = current_values.get("potential_root_causes", [])

        is_failed = current_values.get("capa_generation_status") == "FAILED" and len(recs) == 0
        comp_status = "FAILED" if is_failed else "PAUSED_FOR_HUMAN_REVIEW"

        capa_result = CAPAWorkflowResult(
            workflow_id=workflow_id,
            investigation_id=investigation_id,
            thread_id=active_thread_id,
            rca_summary=f"Problem: {problem_statement or 'Manufacturing excursion'}",
            potential_root_causes=causes,
            capa_recommendations=recs,
            corrective_actions=cas,
            preventive_actions=pas,
            approved_actions=[],
            rejected_actions=[],
            pending_actions=recs,
            validation_errors=val_errors,
            capa_warnings=warns,
            capa_generation_status=current_values.get("capa_generation_status", "COMPLETED"),
            capa_review_status="PENDING_REVIEW",
            human_review_required=True,
            workflow_completion_status=comp_status,
            persisted_in_db=False,
            persisted_capa_ids=[],
            updated_at=datetime.now(timezone.utc),
        )

    # Optional database persistence for reviewable suggestions
    if persist and investigation_id and db is not None:
        from app.services.capa_service import capa_service
        try:
            persisted_actions = capa_service.persist_capa_recommendations(
                db=db,
                investigation_id=investigation_id,
                recommendations=capa_result.capa_recommendations,
            )
            capa_result.persisted_in_db = len(persisted_actions) > 0
            capa_result.persisted_capa_ids = [str(a.id) for a in persisted_actions]
        except Exception as err:
            logger.error("Failed to persist CAPA suggestions to database: %s", err)
            capa_result.capa_warnings.append(f"Database persistence failed: {err}")

    return capa_result


def resume_capa_workflow(
    thread_id: str,
    review_request: CAPAReviewRequest,
    db: Optional[Session] = None,
) -> CAPAWorkflowResult:
    """Resume a paused CAPA workflow thread by applying explicit human review decisions."""
    from fastapi import HTTPException, status
    config = {"configurable": {"thread_id": thread_id}}
    state_snap = capa_workflow.get_state(config)

    if not state_snap or not state_snap.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow thread '{thread_id}' not found.",
        )

    # Verify that thread is currently awaiting an interrupt
    has_interrupt = any(len(task.interrupts) > 0 for task in state_snap.tasks)
    if not has_interrupt:
        if state_snap.values.get("capa_workflow_result"):
            return state_snap.values["capa_workflow_result"]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow thread '{thread_id}' is not currently paused awaiting human review.",
        )

    resume_payload = review_request.model_dump()
    final_output = capa_workflow.invoke(Command(resume=resume_payload), config=config)

    state_snap_after = capa_workflow.get_state(config)
    res_values = state_snap_after.values if state_snap_after else final_output
    capa_result: Optional[CAPAWorkflowResult] = res_values.get("capa_workflow_result")

    if capa_result is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow resumed but failed to assemble final CAPA result.",
        )

    # Persist updated review decisions into PostgreSQL
    inv_id = capa_result.investigation_id
    if inv_id and db is not None:
        from app.services.capa_service import capa_service
        try:
            updated_actions = capa_service.apply_capa_review_decisions(
                db=db,
                investigation_id=inv_id,
                decisions=review_request.decisions,
                reviewer_comments=review_request.general_comments,
            )
            capa_result.persisted_in_db = True
            capa_result.persisted_capa_ids = [str(a.id) for a in updated_actions]
        except Exception as err:
            logger.error("Failed to update reviewed CAPA actions in PostgreSQL: %s", err)
            capa_result.capa_warnings.append(f"PostgreSQL decision update failed: {err}")

    return capa_result



