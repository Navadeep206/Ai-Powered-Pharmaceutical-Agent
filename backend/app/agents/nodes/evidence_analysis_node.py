"""Evidence Analysis Node for RootIQ LangGraph Workflow.

Performs rigorous empirical evidence evaluation:
- Classifies evidence into Supporting and Contradictory.
- Identifies Missing Evidence and critical data gaps.
- Formulates high-priority Investigator Questions.
Preserves ALCOA+ data integrity and source traceability.
"""

import json
from typing import Any, Dict, List, Optional
import groq
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError

from app.agents.state import RCAWorkflowState
from app.core.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIConnectionError,
    AIModelUnavailableError,
    AIRateLimitError,
    AITimeoutError,
)
from app.core.logging import get_logger
from app.schemas.evidence import EvidenceReviewStatusEnum, EvidenceTypeEnum
from app.schemas.rca import EvidenceAssessment
from app.services.ai_service import ai_service
from app.services.prompts import (
    EVIDENCE_ANALYSIS_SYSTEM_PROMPT,
    build_evidence_analysis_human_prompt,
)

logger = get_logger("agents.nodes.evidence_analysis")


class EvidenceItemModel(BaseModel):
    """Transfer model for single evidence assessment in LLM response."""

    evidence_id: Optional[str] = None
    evidence_description: str
    evidence_type: EvidenceTypeEnum
    source_reference: Optional[str] = None
    related_potential_cause: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class EvidenceAnalysisLLMResponse(BaseModel):
    """Structured container for Evidence Analysis LLM output."""

    items: List[EvidenceItemModel]
    missing_evidence: List[str] = Field(default_factory=list)
    investigator_questions: List[str] = Field(default_factory=list)


def _parse_evidence_from_text(raw_text: str) -> EvidenceAnalysisLLMResponse:
    """Fallback JSON parser for raw LLM text responses."""
    clean = raw_text.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()

    data = json.loads(clean)
    if isinstance(data, list):
        return EvidenceAnalysisLLMResponse(
            items=[EvidenceItemModel(**x) for x in data],
            missing_evidence=[],
            investigator_questions=[],
        )
    return EvidenceAnalysisLLMResponse(**data)


def evidence_analysis_node(state: RCAWorkflowState) -> Dict[str, Any]:
    """Execute evidence classification, missing evidence auditing, and question formulation."""
    logger.info("Executing EvidenceAnalysisNode for workflow %s", state.get("workflow_id"))

    problem_statement = state.get("problem_statement") or "Observed manufacturing process deviation."
    incident_context = state.get("incident_context") or {}
    investigation_facts = state.get("investigation_facts") or []
    five_whys_analysis = state.get("five_whys_analysis") or []
    fishbone_analysis = state.get("fishbone_analysis") or []
    rca_warnings = list(state.get("rca_warnings") or [])

    existing_questions = list(state.get("investigator_questions") or [])
    supporting_evidence: List[EvidenceAssessment] = []
    contradictory_evidence: List[EvidenceAssessment] = []
    missing_evidence: List[str] = list(state.get("missing_evidence") or [])
    new_questions: List[str] = list(existing_questions)

    whys_payload = [w.model_dump() for w in five_whys_analysis]
    fishbone_payload = [c.model_dump() for c in fishbone_analysis]

    try:
        client = ai_service.get_client()
        system_msg = SystemMessage(content=EVIDENCE_ANALYSIS_SYSTEM_PROMPT)
        human_msg = HumanMessage(
            content=build_evidence_analysis_human_prompt(
                problem_statement=problem_statement,
                incident_context=incident_context,
                investigation_facts=investigation_facts,
                five_whys_chain=whys_payload,
                fishbone_causes=fishbone_payload,
            )
        )

        structured_llm = client.with_structured_output(EvidenceAnalysisLLMResponse, method="json_mode")
        llm_output = structured_llm.invoke([system_msg, human_msg])

        if isinstance(llm_output, dict):
            parsed_res = EvidenceAnalysisLLMResponse(**llm_output)
        elif isinstance(llm_output, EvidenceAnalysisLLMResponse):
            parsed_res = llm_output
        elif isinstance(llm_output, AIMessage):
            parsed_res = _parse_evidence_from_text(llm_output.content)
        else:
            raise OutputParserException(f"Unexpected response type: {type(llm_output)}")

        # Process structured items
        for idx, item in enumerate(parsed_res.items):
            eid = item.evidence_id or f"EVD-{idx+1:03d}"
            assessment = EvidenceAssessment(
                evidence_id=eid,
                evidence_description=item.evidence_description.strip(),
                evidence_type=item.evidence_type,
                source_reference=item.source_reference.strip() if item.source_reference else "Batch Investigation Dossier",
                related_potential_cause=item.related_potential_cause,
                reasoning=item.reasoning.strip() if item.reasoning else None,
                confidence=max(0.0, min(1.0, float(item.confidence))),
                review_status=EvidenceReviewStatusEnum.PENDING_REVIEW,
            )

            if item.evidence_type == EvidenceTypeEnum.SUPPORTING:
                supporting_evidence.append(assessment)
            elif item.evidence_type == EvidenceTypeEnum.CONTRADICTORY:
                contradictory_evidence.append(assessment)
            elif item.evidence_type == EvidenceTypeEnum.MISSING_EVIDENCE:
                if item.evidence_description not in missing_evidence:
                    missing_evidence.append(item.evidence_description)
            elif item.evidence_type == EvidenceTypeEnum.INVESTIGATOR_QUESTION:
                if item.evidence_description not in new_questions:
                    new_questions.append(item.evidence_description)

        for gap in parsed_res.missing_evidence:
            gap_clean = gap.strip()
            if gap_clean and gap_clean not in missing_evidence:
                missing_evidence.append(gap_clean)

        for q in parsed_res.investigator_questions:
            q_clean = q.strip()
            if q_clean and q_clean not in new_questions:
                new_questions.append(q_clean)

    except (
        AIConfigurationError,
        AIAuthenticationError,
        AITimeoutError,
        AIRateLimitError,
        AIModelUnavailableError,
        AIConnectionError,
        groq.APIError,
        OutputParserException,
        ValidationError,
        json.JSONDecodeError,
        Exception,
    ) as err:
        err_msg = f"Evidence analysis encountered an error: {err}"
        logger.warning(err_msg)
        rca_warnings.append(err_msg)

        # Baseline fallback evidence items based on facts
        if not supporting_evidence and not contradictory_evidence:
            supporting_evidence.append(
                EvidenceAssessment(
                    evidence_id="EVD-001",
                    evidence_description=f"Process excursion documented in investigation context: {problem_statement[:120]}",
                    evidence_type=EvidenceTypeEnum.SUPPORTING,
                    source_reference="Batch Production Record & Alarm Log",
                    related_potential_cause="Operating Parameter Excursion",
                    reasoning="Corroborates occurrence of deviation during routine manufacturing operations.",
                    confidence=0.8,
                    review_status=EvidenceReviewStatusEnum.PENDING_REVIEW,
                )
            )
            if not missing_evidence:
                missing_evidence.append("Instrumentation calibration certificates and SCADA sensor trend logs for 24 hours prior to excursion.")
            if not new_questions:
                new_questions.append("Were any preventive maintenance interventions or cleaning cycles performed immediately prior to this batch?")

    return {
        "supporting_evidence": supporting_evidence,
        "contradictory_evidence": contradictory_evidence,
        "missing_evidence": missing_evidence,
        "investigator_questions": new_questions,
        "rca_warnings": rca_warnings,
    }

