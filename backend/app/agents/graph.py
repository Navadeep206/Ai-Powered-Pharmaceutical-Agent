"""LangGraph Workflow Orchestration for RootIQ Incident Extraction.

Builds and compiles the StateGraph routing input processing, structured extraction,
Pydantic validation, GxP quality assessment, and finalization with MemorySaver checkpointing.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes.extraction_node import incident_extraction_node
from app.agents.nodes.finalization_node import finalization_node
from app.agents.nodes.input_node import input_processing_node
from app.agents.nodes.quality_node import quality_assessment_node
from app.agents.nodes.validation_node import structured_validation_node
from app.agents.state import ExtractionWorkflowState
from app.core.logging import get_logger
from app.schemas.document import NormalizedIncidentIntake
from app.schemas.extraction import ExtractionAnalysisResponse

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
