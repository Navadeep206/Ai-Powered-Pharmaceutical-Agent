"""CAPA Generation Node for RootIQ LangGraph Workflow.

Synthesizes evidence-based Corrective and Preventive Action (CAPA) recommendations
tied directly to identified root causes, contributing factors, and empirical observations.
Enforces structured effectiveness verification plans adhering to FDA/ICH Q10.
"""

import json
from typing import Any, Dict, List, Optional
import groq
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import AliasChoices, BaseModel, Field, ValidationError

from app.agents.state import CAPAWorkflowState
from app.core.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIConnectionError,
    AIModelUnavailableError,
    AIRateLimitError,
    AITimeoutError,
)
from app.core.logging import get_logger
from app.schemas.capa import (
    CAPARecommendation,
    CAPAStatusEnum,
    CAPATypeEnum,
    EffectivenessVerificationPlan,
)
from app.services.ai_service import ai_service
from app.services.prompts import (
    CAPA_GENERATION_SYSTEM_PROMPT,
    build_capa_generation_human_prompt,
)

logger = get_logger("agents.nodes.capa_generation")


class EffectivenessVerificationPlanModel(BaseModel):
    """Pydantic transfer model for effectiveness verification from LLM."""

    measurable_outcome: str = Field(
        ...,
        validation_alias=AliasChoices("measurable_outcome", "outcome", "target_criteria"),
    )
    verification_method: str = Field(
        ...,
        validation_alias=AliasChoices("verification_method", "method", "protocol"),
    )
    evidence_required: str = Field(
        ...,
        validation_alias=AliasChoices("evidence_required", "evidence", "documentation_required"),
    )
    suggested_verifier_role: str = Field(
        default="QA Compliance Specialist",
        validation_alias=AliasChoices("suggested_verifier_role", "verifier_role", "verifier"),
    )
    verification_timeframe: str = Field(
        default="Within 30 days post-implementation",
        validation_alias=AliasChoices("verification_timeframe", "timeframe", "duration"),
    )
    failure_criteria: str = Field(
        default="Any recurrence of deviation parameter excursion",
        validation_alias=AliasChoices("failure_criteria", "failure_condition"),
    )


class CAPARecommendationItemModel(BaseModel):
    """Pydantic transfer model for a single CAPA suggestion from LLM."""

    capa_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("capa_id", "id"))
    action_type: CAPATypeEnum
    description: str = Field(..., validation_alias=AliasChoices("description", "action_description", "action"))
    related_root_cause_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("related_root_cause_id", "root_cause_id"),
    )
    rationale: str = Field(
        default="",
        validation_alias=AliasChoices("rationale", "justification", "reasoning"),
    )
    supporting_evidence_references: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("supporting_evidence_references", "evidence_references", "supporting_evidence"),
    )
    assumptions: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    suggested_owner_role: str = Field(
        default="Quality Assurance",
        validation_alias=AliasChoices("suggested_owner_role", "owner_role", "action_owner"),
    )
    suggested_target_date: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("suggested_target_date", "target_date"),
    )
    effectiveness_verification: EffectivenessVerificationPlanModel


class CAPAGenerationLLMResponse(BaseModel):
    """Structured container for CAPA generation LLM output."""

    recommendations: List[CAPARecommendationItemModel]


def _parse_capa_from_text(raw_text: str) -> CAPAGenerationLLMResponse:
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
        return CAPAGenerationLLMResponse(
            recommendations=[CAPARecommendationItemModel(**x) for x in data]
        )
    return CAPAGenerationLLMResponse(**data)


def capa_generation_node(state: CAPAWorkflowState) -> Dict[str, Any]:
    """Execute AI-assisted CAPA recommendations generation."""
    logger.info("Executing CAPAGenerationNode for workflow %s", state.get("workflow_id"))

    problem_statement = state.get("problem_statement") or "Observed manufacturing process deviation."
    potential_root_causes = state.get("potential_root_causes") or []
    contributing_factors = state.get("contributing_factors") or []
    supporting_evidence = state.get("supporting_evidence") or []
    contradictory_evidence = state.get("contradictory_evidence") or []
    missing_evidence = state.get("missing_evidence") or []
    capa_warnings = list(state.get("capa_warnings") or [])

    recommendations: List[CAPARecommendation] = []
    corrective_actions: List[CAPARecommendation] = []
    preventive_actions: List[CAPARecommendation] = []
    generation_status = "COMPLETED"

    causes_payload = [c.model_dump() for c in potential_root_causes]
    factors_payload = [f.model_dump() for f in contributing_factors]
    sup_payload = [e.model_dump() for e in supporting_evidence]
    contra_payload = [e.model_dump() for e in contradictory_evidence]

    try:
        client = ai_service.get_client()
        system_msg = SystemMessage(content=CAPA_GENERATION_SYSTEM_PROMPT)
        human_msg = HumanMessage(
            content=build_capa_generation_human_prompt(
                problem_statement=problem_statement,
                potential_root_causes=causes_payload,
                contributing_factors=factors_payload,
                supporting_evidence=sup_payload,
                contradictory_evidence=contra_payload,
                missing_evidence=missing_evidence,
            )
        )

        structured_llm = client.with_structured_output(CAPAGenerationLLMResponse, method="json_mode")
        llm_output = structured_llm.invoke([system_msg, human_msg])

        if isinstance(llm_output, dict):
            parsed_res = CAPAGenerationLLMResponse(**llm_output)
        elif isinstance(llm_output, CAPAGenerationLLMResponse):
            parsed_res = llm_output
        elif isinstance(llm_output, AIMessage):
            parsed_res = _parse_capa_from_text(llm_output.content)
        else:
            raise OutputParserException(f"Unexpected response type: {type(llm_output)}")

        for idx, item in enumerate(parsed_res.recommendations):
            cid = item.capa_id or f"CAPA-REC-{idx+1:02d}"

            eff_plan = EffectivenessVerificationPlan(
                measurable_outcome=item.effectiveness_verification.measurable_outcome.strip(),
                verification_method=item.effectiveness_verification.verification_method.strip(),
                evidence_required=item.effectiveness_verification.evidence_required.strip(),
                suggested_verifier_role=item.effectiveness_verification.suggested_verifier_role.strip(),
                verification_timeframe=item.effectiveness_verification.verification_timeframe.strip(),
                failure_criteria=item.effectiveness_verification.failure_criteria.strip(),
            )

            rec = CAPARecommendation(
                capa_id=cid,
                action_type=item.action_type,
                description=item.description.strip(),
                related_root_cause_id=item.related_root_cause_id,
                rationale=item.rationale.strip(),
                supporting_evidence_references=item.supporting_evidence_references,
                assumptions=item.assumptions,
                dependencies=item.dependencies,
                suggested_owner_role=item.suggested_owner_role.strip(),
                suggested_target_date=item.suggested_target_date,
                effectiveness_verification=eff_plan,
                review_status=CAPAStatusEnum.PROPOSED,
                assigned_owner=None,
                actual_target_date=None,
                reviewer_comments=None,
            )

            recommendations.append(rec)
            if rec.action_type == CAPATypeEnum.CORRECTIVE_ACTION:
                corrective_actions.append(rec)
            else:
                preventive_actions.append(rec)

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
        err_msg = f"CAPA generation encountered an error: {err}"
        logger.warning(err_msg)
        capa_warnings.append(err_msg)
        generation_status = "FAILED"

        # Baseline fallback generation if root causes are present
        if not recommendations:
            primary_cause = potential_root_causes[0] if potential_root_causes else None
            cause_desc = primary_cause.cause_description if primary_cause else problem_statement
            cause_id = primary_cause.cause_id if primary_cause else None

            # 1. Corrective action
            ca_plan = EffectivenessVerificationPlan(
                measurable_outcome="Zero process parameter excursions or seal leaks during subsequent batch processing.",
                verification_method="Continuous SCADA telemetry monitoring and batch record QA audit.",
                evidence_required="Completed Batch Production Records and SCADA alarm history logs.",
                suggested_verifier_role="Quality Assurance Specialist",
                verification_timeframe="Next 3 consecutive commercial batches",
                failure_criteria="Any recurrence of similar deviation within 3 commercial production runs.",
            )
            ca_rec = CAPARecommendation(
                capa_id="CAPA-REC-01",
                action_type=CAPATypeEnum.CORRECTIVE_ACTION,
                description=f"Inspect, calibrate, and repair identified failure mechanism: {cause_desc[:120]}.",
                related_root_cause_id=cause_id,
                rationale="Direct corrective intervention required to restore validated equipment operating state.",
                supporting_evidence_references=[e.description for e in supporting_evidence[:2]],
                assumptions=["Preliminary recommendation generated via fallback; investigator review required."],
                dependencies=["Equipment lock-out/tag-out during scheduled maintenance window."],
                suggested_owner_role="Senior Maintenance Engineer",
                suggested_target_date="+30 days",
                effectiveness_verification=ca_plan,
                review_status=CAPAStatusEnum.PROPOSED,
            )
            recommendations.append(ca_rec)
            corrective_actions.append(ca_rec)

            # 2. Preventive action
            pa_plan = EffectivenessVerificationPlan(
                measurable_outcome="100% adherence to updated inspection and maintenance schedules.",
                verification_method="Monthly CMMS maintenance audit and pre-batch check verification.",
                evidence_required="Signed preventive maintenance work orders and pre-flight logs.",
                suggested_verifier_role="Engineering Manager",
                verification_timeframe="6 months post-implementation",
                failure_criteria="Overdue PM work order or unaddressed pre-batch equipment warning.",
            )
            pa_rec = CAPARecommendation(
                capa_id="CAPA-REC-02",
                action_type=CAPATypeEnum.PREVENTIVE_ACTION,
                description="Review and update preventive maintenance intervals, telemetry monitoring, and SOP procedures.",
                related_root_cause_id=cause_id,
                rationale="Prevent recurrence by addressing systemic equipment lifecycle maintenance intervals.",
                supporting_evidence_references=[f.description for f in contributing_factors[:2]],
                assumptions=["Preventive maintenance interval extension was a contributing risk factor."],
                dependencies=["Engineering change control and QA SOP revision approval."],
                suggested_owner_role="Lead Automation / Reliability Engineer",
                suggested_target_date="+60 days",
                effectiveness_verification=pa_plan,
                review_status=CAPAStatusEnum.PROPOSED,
            )
            recommendations.append(pa_rec)
            preventive_actions.append(pa_rec)

    return {
        "capa_recommendations": recommendations,
        "corrective_actions": corrective_actions,
        "preventive_actions": preventive_actions,
        "capa_warnings": capa_warnings,
        "capa_generation_status": generation_status,
        "capa_review_status": "PENDING_REVIEW",
        "human_review_required": True,
    }
