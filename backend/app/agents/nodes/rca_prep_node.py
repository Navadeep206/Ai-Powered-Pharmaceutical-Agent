"""RCA Preparation Node for RootIQ LangGraph Workflow.

Normalizes problem statement, incident context, and factual telemetry data
prior to causal reasoning steps.
"""

from typing import Any, Dict, List
from app.agents.state import RCAWorkflowState
from app.core.logging import get_logger

logger = get_logger("agents.nodes.rca_prep")


def rca_prep_node(state: RCAWorkflowState) -> Dict[str, Any]:
    """Formulate clean problem statement and assemble baseline factual context."""
    logger.info("Executing RCAPrepNode for workflow %s", state.get("workflow_id"))

    incident_context = dict(state.get("incident_context") or {})
    investigation_facts: List[Dict[str, Any]] = list(state.get("investigation_facts") or [])
    rca_warnings: List[str] = list(state.get("rca_warnings") or [])

    # Check if extracted_data is available in state to enrich context
    extracted_data = state.get("extracted_data")
    if extracted_data and not incident_context:
        # Populate context from extracted data
        if hasattr(extracted_data, "incident_title") and extracted_data.incident_title.value:
            incident_context["title"] = extracted_data.incident_title.value
        if hasattr(extracted_data, "incident_description") and extracted_data.incident_description.value:
            incident_context["description"] = extracted_data.incident_description.value
        if hasattr(extracted_data, "batch_number") and extracted_data.batch_number.value:
            incident_context["batch_number"] = extracted_data.batch_number.value
        if hasattr(extracted_data, "equipment_id") and extracted_data.equipment_id.value:
            incident_context["equipment_id"] = extracted_data.equipment_id.value
        if hasattr(extracted_data, "actual_condition") and extracted_data.actual_condition.value:
            incident_context["actual_condition"] = extracted_data.actual_condition.value
        if hasattr(extracted_data, "expected_condition") and extracted_data.expected_condition.value:
            incident_context["expected_condition"] = extracted_data.expected_condition.value

    # Formulate problem statement
    problem_statement = state.get("problem_statement")
    if not problem_statement or not problem_statement.strip():
        # Formulate from incident context
        title = incident_context.get("title") or incident_context.get("incident_title")
        actual = incident_context.get("actual_condition")
        expected = incident_context.get("expected_condition")
        desc = incident_context.get("description") or incident_context.get("incident_description")

        if actual and expected:
            problem_statement = f"{title or 'Process Excursion'}: Observed {actual} against expected standard of {expected}."
        elif title and desc:
            problem_statement = f"{title}: {desc[:200]}"
        elif title:
            problem_statement = str(title)
        elif desc:
            problem_statement = str(desc[:200])
        else:
            problem_statement = "Unspecified manufacturing process deviation requiring systematic root cause analysis."

    # Enrich facts if empty
    if not investigation_facts:
        if "batch_number" in incident_context:
            investigation_facts.append({"fact_type": "Batch", "detail": f"Batch Number: {incident_context['batch_number']}"})
        if "equipment_id" in incident_context:
            investigation_facts.append({"fact_type": "Equipment", "detail": f"Equipment ID: {incident_context['equipment_id']}"})
        if "actual_condition" in incident_context:
            investigation_facts.append({"fact_type": "Excursion", "detail": f"Observed: {incident_context['actual_condition']}"})
        if "expected_condition" in incident_context:
            investigation_facts.append({"fact_type": "Specification", "detail": f"Specification: {incident_context['expected_condition']}"})

    return {
        "problem_statement": problem_statement.strip(),
        "incident_context": incident_context,
        "investigation_facts": investigation_facts,
        "rca_warnings": rca_warnings,
        "rca_status": "In Progress",
        "human_review_required": True,
    }

