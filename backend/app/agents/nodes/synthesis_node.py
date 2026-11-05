"""RCA Synthesis Node for RootIQ LangGraph Workflow.

Synthesizes findings from Five Whys, Ishikawa 6M categories, and Evidence Assessment
into candidate root causes and secondary contributing factors.
Preserves multiple competing hypotheses when empirical evidence is inconclusive,
ensuring strict adherence to GxP human-in-the-loop review requirements.
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
    ContributingFactor,
    PotentialRootCause,
)
from app.services.ai_service import ai_service
from app.services.prompts import (
    RCA_SYNTHESIS_SYSTEM_PROMPT,
    build_synthesis_human_prompt,
)

logger = get_logger("agents.nodes.synthesis")


class PotentialRootCauseItemModel(BaseModel):
    """Transfer model for candidate root cause in LLM response."""

    cause_id: Optional[str] = None
    cause_description: str
    cause_category: str
    source_method: str = "Combined"
    supporting_evidence: List[str] = Field(default_factory=list)
    contradictory_evidence: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    rationale: str
    uncertainty_notes: Optional[str] = None


class ContributingFactorItemModel(BaseModel):
    """Transfer model for secondary contributing factor in LLM response."""

    factor_id: Optional[str] = None
    description: str
    category: str
    related_cause_id: Optional[str] = None
    supporting_evidence: List[str] = Field(default_factory=list)


class SynthesisLLMResponse(BaseModel):
    """Structured container for RCA Synthesis LLM output."""

    potential_root_causes: List[PotentialRootCauseItemModel]
    contributing_factors: List[ContributingFactorItemModel]


def _parse_synthesis_from_text(raw_text: str) -> SynthesisLLMResponse:
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
    return SynthesisLLMResponse(**data)


def synthesis_node(state: RCAWorkflowState) -> Dict[str, Any]:
    """Execute synthesis of candidate root causes and secondary factors."""
    logger.info("Executing SynthesisNode for workflow %s", state.get("workflow_id"))

    problem_statement = state.get("problem_statement") or "Observed manufacturing process deviation."
    five_whys_analysis = state.get("five_whys_analysis") or []
    fishbone_analysis = state.get("fishbone_analysis") or []
    supporting_evidence = state.get("supporting_evidence") or []
    contradictory_evidence = state.get("contradictory_evidence") or []
    rca_warnings = list(state.get("rca_warnings") or [])

    potential_root_causes: List[PotentialRootCause] = []
    contributing_factors: List[ContributingFactor] = []

    whys_payload = [w.model_dump() for w in five_whys_analysis]
    fishbone_payload = [c.model_dump() for c in fishbone_analysis]
    evidence_payload = [e.model_dump() for e in supporting_evidence] + [e.model_dump() for e in contradictory_evidence]

    try:
        client = ai_service.get_client()
        system_msg = SystemMessage(content=RCA_SYNTHESIS_SYSTEM_PROMPT)
        human_msg = HumanMessage(
            content=build_synthesis_human_prompt(
                problem_statement=problem_statement,
                five_whys_chain=whys_payload,
                fishbone_causes=fishbone_payload,
                evidence_items=evidence_payload,
            )
        )

        structured_llm = client.with_structured_output(SynthesisLLMResponse, method="json_mode")
        llm_output = structured_llm.invoke([system_msg, human_msg])

        if isinstance(llm_output, dict):
            parsed_res = SynthesisLLMResponse(**llm_output)
        elif isinstance(llm_output, SynthesisLLMResponse):
            parsed_res = llm_output
        elif isinstance(llm_output, AIMessage):
            parsed_res = _parse_synthesis_from_text(llm_output.content)
        else:
            raise OutputParserException(f"Unexpected response type: {type(llm_output)}")

        for idx, item in enumerate(parsed_res.potential_root_causes):
            pid = item.cause_id or f"PRC-{idx+1:02d}"
            status = (
                CauseVerificationStatusEnum.EVIDENCE_SUPPORTED
                if item.supporting_evidence
                else CauseVerificationStatusEnum.AI_SUGGESTION
            )

            potential_root_causes.append(
                PotentialRootCause(
                    cause_id=pid,
                    cause_description=item.cause_description.strip(),
                    cause_category=item.cause_category.strip(),
                    source_method=item.source_method.strip(),
                    supporting_evidence=item.supporting_evidence,
                    contradictory_evidence=item.contradictory_evidence,
                    confidence=max(0.0, min(1.0, float(item.confidence))),
                    rationale=item.rationale.strip(),
                    uncertainty_notes=item.uncertainty_notes.strip() if item.uncertainty_notes else None,
                    review_status=status,
                )
            )

        for idx, item in enumerate(parsed_res.contributing_factors):
            cfid = item.factor_id or f"CF-{idx+1:02d}"
            contributing_factors.append(
                ContributingFactor(
                    factor_id=cfid,
                    description=item.description.strip(),
                    category=item.category.strip(),
                    related_cause_id=item.related_cause_id,
                    supporting_evidence=item.supporting_evidence,
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
        err_msg = f"RCA synthesis encountered an error: {err}"
        logger.warning(err_msg)
        rca_warnings.append(err_msg)

        # Baseline fallback synthesis using terminal why or fishbone
        if not potential_root_causes:
            terminal_why = next((w for w in five_whys_analysis if w.is_root_cause), None)
            desc = terminal_why.answer if terminal_why else "Equipment or procedural excursion requiring root cause verification."
            rationale = terminal_why.reasoning if terminal_why and terminal_why.reasoning else "Designated from terminal Why causal analysis."

            potential_root_causes.append(
                PotentialRootCause(
                    cause_id="PRC-01",
                    cause_description=desc,
                    cause_category="Machine / Method",
                    source_method="Five Whys",
                    supporting_evidence=[e.description for e in supporting_evidence],
                    contradictory_evidence=[e.description for e in contradictory_evidence],
                    confidence=0.65,
                    rationale=rationale,
                    uncertainty_notes="Preliminary AI synthesis; human investigator review required.",
                    review_status=CauseVerificationStatusEnum.AI_SUGGESTION,
                )
            )

        if not contributing_factors and fishbone_analysis:
            contributing_factors.append(
                ContributingFactor(
                    factor_id="CF-01",
                    description=fishbone_analysis[0].cause_description,
                    category=(
                        fishbone_analysis[0].category.value
                        if hasattr(fishbone_analysis[0].category, "value")
                        else str(fishbone_analysis[0].category)
                    ),
                    related_cause_id="PRC-01",
                    supporting_evidence=fishbone_analysis[0].supporting_evidence_references,
                )
            )

    return {
        "potential_root_causes": potential_root_causes,
        "contributing_factors": contributing_factors,
        "rca_warnings": rca_warnings,
    }

