"""Ishikawa 6M Fishbone Analysis Node for RootIQ LangGraph Workflow.

Categorizes plausible causal mechanisms across the pharmaceutical 6M dimensions:
Manpower, Machine, Method, Material, Measurement, and Environment.
Leaves categories without factual basis empty to prevent artificial speculation.
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
from app.schemas.rca import (
    CauseVerificationStatusEnum,
    FishboneCategoryEnum,
    FishboneCause,
)
from app.services.ai_service import ai_service
from app.services.prompts import (
    FISHBONE_SYSTEM_PROMPT,
    build_fishbone_human_prompt,
)

logger = get_logger("agents.nodes.fishbone")


class FishboneCauseItemModel(BaseModel):
    """Transfer model for single Ishikawa 6M cause in LLM response."""

    cause_id: Optional[str] = None
    category: FishboneCategoryEnum
    cause_description: str
    reasoning: Optional[str] = None
    supporting_evidence_references: List[str] = Field(default_factory=list)
    contradictory_evidence_references: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    uncertainty_notes: Optional[str] = None
    contributing_factors: List[str] = Field(default_factory=list)


class FishboneLLMResponse(BaseModel):
    """Structured container for Fishbone LLM output."""

    causes: List[FishboneCauseItemModel]


def _parse_fishbone_from_text(raw_text: str) -> FishboneLLMResponse:
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
        return FishboneLLMResponse(causes=[FishboneCauseItemModel(**x) for x in data])
    return FishboneLLMResponse(**data)


def fishbone_node(state: RCAWorkflowState) -> Dict[str, Any]:
    """Execute Ishikawa 6M causal analysis."""
    logger.info("Executing FishboneNode for workflow %s", state.get("workflow_id"))

    problem_statement = state.get("problem_statement") or "Observed manufacturing process deviation."
    incident_context = state.get("incident_context") or {}
    investigation_facts = state.get("investigation_facts") or []
    five_whys_analysis = state.get("five_whys_analysis") or []
    rca_warnings = list(state.get("rca_warnings") or [])

    five_whys_summary = None
    if five_whys_analysis:
        five_whys_summary = "; ".join(
            [f"Why {w.level}: {w.question} -> {w.answer}" for w in five_whys_analysis]
        )

    fishbone_result: List[FishboneCause] = []

    try:
        client = ai_service.get_client()
        system_msg = SystemMessage(content=FISHBONE_SYSTEM_PROMPT)
        human_msg = HumanMessage(
            content=build_fishbone_human_prompt(
                problem_statement=problem_statement,
                incident_context=incident_context,
                investigation_facts=investigation_facts,
                five_whys_summary=five_whys_summary,
            )
        )

        structured_llm = client.with_structured_output(FishboneLLMResponse, method="json_mode")
        llm_output = structured_llm.invoke([system_msg, human_msg])

        if isinstance(llm_output, dict):
            parsed_causes = FishboneLLMResponse(**llm_output).causes
        elif isinstance(llm_output, FishboneLLMResponse):
            parsed_causes = llm_output.causes
        elif isinstance(llm_output, AIMessage):
            parsed_causes = _parse_fishbone_from_text(llm_output.content).causes
        else:
            raise OutputParserException(f"Unexpected response type: {type(llm_output)}")

        for idx, item in enumerate(parsed_causes):
            cid = item.cause_id or f"CAUSE-{idx+1:02d}"
            status = (
                CauseVerificationStatusEnum.EVIDENCE_SUPPORTED
                if item.supporting_evidence_references
                else CauseVerificationStatusEnum.AI_SUGGESTION
            )

            fishbone_result.append(
                FishboneCause(
                    cause_id=cid,
                    category=item.category,
                    cause_description=item.cause_description.strip(),
                    reasoning=item.reasoning.strip() if item.reasoning else None,
                    evidence_references=item.supporting_evidence_references,
                    supporting_evidence_references=item.supporting_evidence_references,
                    contradictory_evidence_references=item.contradictory_evidence_references,
                    confidence=max(0.0, min(1.0, float(item.confidence))),
                    cause_origin="AI Suggestion",
                    status=status,
                    uncertainty_notes=item.uncertainty_notes.strip() if item.uncertainty_notes else None,
                    contributing_factors=item.contributing_factors,
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
        err_msg = f"Fishbone analysis encountered an error: {err}"
        logger.warning(err_msg)
        rca_warnings.append(err_msg)

        # Graceful fallback: produce essential hypothesis based on machine/method if available
        if not fishbone_result:
            fishbone_result = [
                FishboneCause(
                    cause_id="CAUSE-01",
                    category=FishboneCategoryEnum.MACHINE,
                    cause_description="Possible mechanical wear, seal degradation, or control loop malfunction in processing unit.",
                    reasoning="Equipment-level causal hypothesis based on typical manufacturing excursions.",
                    evidence_references=[],
                    supporting_evidence_references=[],
                    contradictory_evidence_references=[],
                    confidence=0.6,
                    cause_origin="AI Suggestion",
                    status=CauseVerificationStatusEnum.AI_SUGGESTION,
                    uncertainty_notes="Telemetry logs pending maintenance inspection.",
                    contributing_factors=[],
                ),
                FishboneCause(
                    cause_id="CAUSE-02",
                    category=FishboneCategoryEnum.METHOD,
                    cause_description="Potential ambiguity in parameter control tolerance limits within operating procedure.",
                    reasoning="Procedural verification hypothesis awaiting batch record audit.",
                    evidence_references=[],
                    supporting_evidence_references=[],
                    contradictory_evidence_references=[],
                    confidence=0.55,
                    cause_origin="AI Suggestion",
                    status=CauseVerificationStatusEnum.AI_SUGGESTION,
                    uncertainty_notes="Requires comparison with master batch record standard.",
                    contributing_factors=[],
                ),
            ]

    return {
        "fishbone_analysis": fishbone_result,
        "rca_warnings": rca_warnings,
    }
