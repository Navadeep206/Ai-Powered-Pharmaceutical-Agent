"""Five Whys Reasoning Node for RootIQ LangGraph Workflow.

Executes sequential causal depth analysis drilling down from observed deviation
to underlying physical or systemic failure mechanisms without artificial padding.
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
from app.schemas.rca import CauseVerificationStatusEnum, FiveWhysLevel
from app.services.ai_service import ai_service
from app.services.prompts import (
    FIVE_WHYS_SYSTEM_PROMPT,
    build_five_whys_human_prompt,
)

logger = get_logger("agents.nodes.five_whys")


class FiveWhysItemModel(BaseModel):
    """Transfer model for single Why level in LLM response."""

    level: int = Field(..., ge=1, le=5)
    question: str
    answer: str
    reasoning: Optional[str] = None
    supporting_evidence_references: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    uncertainty_notes: Optional[str] = None
    is_root_cause: bool = False


class FiveWhysLLMResponse(BaseModel):
    """Structured container for 5-Whys LLM output."""

    chain: List[FiveWhysItemModel]


def _parse_five_whys_from_text(raw_text: str) -> FiveWhysLLMResponse:
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
        return FiveWhysLLMResponse(chain=[FiveWhysItemModel(**x) for x in data])
    return FiveWhysLLMResponse(**data)


def five_whys_node(state: RCAWorkflowState) -> Dict[str, Any]:
    """Execute Five Whys causal chain analysis."""
    logger.info("Executing FiveWhysNode for workflow %s", state.get("workflow_id"))

    problem_statement = state.get("problem_statement") or "Observed manufacturing process deviation."
    incident_context = state.get("incident_context") or {}
    investigation_facts = state.get("investigation_facts") or []
    rca_warnings = list(state.get("rca_warnings") or [])

    five_whys_result: List[FiveWhysLevel] = []

    try:
        client = ai_service.get_client()
        system_msg = SystemMessage(content=FIVE_WHYS_SYSTEM_PROMPT)
        human_msg = HumanMessage(
            content=build_five_whys_human_prompt(
                problem_statement=problem_statement,
                incident_context=incident_context,
                investigation_facts=investigation_facts,
            )
        )

        structured_llm = client.with_structured_output(FiveWhysLLMResponse, method="json_mode")
        llm_output = structured_llm.invoke([system_msg, human_msg])

        if isinstance(llm_output, dict):
            parsed_chain = FiveWhysLLMResponse(**llm_output).chain
        elif isinstance(llm_output, FiveWhysLLMResponse):
            parsed_chain = llm_output.chain
        elif isinstance(llm_output, AIMessage):
            parsed_chain = _parse_five_whys_from_text(llm_output.content).chain
        else:
            raise OutputParserException(f"Unexpected response type: {type(llm_output)}")

        # Validate sequence, ensure level 1..N and designate root cause
        total_items = min(len(parsed_chain), 5)
        for idx in range(total_items):
            item = parsed_chain[idx]
            is_terminal = idx == (total_items - 1)
            # Determine appropriate review status: EVIDENCE_SUPPORTED if citations present, else AI_SUGGESTION
            status = (
                CauseVerificationStatusEnum.EVIDENCE_SUPPORTED
                if item.supporting_evidence_references
                else CauseVerificationStatusEnum.AI_SUGGESTION
            )

            five_whys_result.append(
                FiveWhysLevel(
                    level=idx + 1,
                    question=item.question.strip(),
                    answer=item.answer.strip(),
                    reasoning=item.reasoning.strip() if item.reasoning else None,
                    supporting_evidence_references=item.supporting_evidence_references,
                    evidence_references=item.supporting_evidence_references,
                    confidence=max(0.0, min(1.0, float(item.confidence))),
                    uncertainty_notes=item.uncertainty_notes.strip() if item.uncertainty_notes else None,
                    is_root_cause=is_terminal,
                    status=status,
                )
            )

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
        err_msg = f"Five Whys reasoning encountered an error: {err}"
        logger.warning(err_msg)
        rca_warnings.append(err_msg)

        # Fallback graceful preliminary causal chain if empty
        if not five_whys_result:
            five_whys_result = [
                FiveWhysLevel(
                    level=1,
                    question=f"Why did '{problem_statement[:80]}' occur?",
                    answer="Anomalous operating excursion detected during batch processing.",
                    reasoning="Preliminary observation derived directly from incident intake.",
                    supporting_evidence_references=[],
                    evidence_references=[],
                    confidence=0.6,
                    uncertainty_notes="Preliminary AI generation; detailed causal links require investigator review.",
                    is_root_cause=False,
                    status=CauseVerificationStatusEnum.AI_SUGGESTION,
                ),
                FiveWhysLevel(
                    level=2,
                    question="Why did the anomalous operating excursion occur?",
                    answer="Suspected deviation from validated process control parameters or equipment state.",
                    reasoning="Generic upstream failure mode pending telemetry and calibration confirmation.",
                    supporting_evidence_references=[],
                    evidence_references=[],
                    confidence=0.5,
                    uncertainty_notes="Awaiting specific equipment inspection records.",
                    is_root_cause=True,
                    status=CauseVerificationStatusEnum.AI_SUGGESTION,
                ),
            ]

    return {
        "five_whys_analysis": five_whys_result,
        "rca_warnings": rca_warnings,
    }

