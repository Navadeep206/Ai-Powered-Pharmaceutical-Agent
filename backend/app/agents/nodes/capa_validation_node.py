"""CAPA Validation Node for RootIQ LangGraph Workflow.

Audits AI-generated CAPA recommendations against pharmaceutical regulatory rules:
- Verifies action classification (Corrective vs. Preventive).
- Enforces non-generic descriptions (minimum length and technical specificity).
- Validates root cause and contributing factor linkages.
- Verifies comprehensive effectiveness verification plans.
- Checks owner role assignments and review status boundaries.
- Detects duplicate or substantially overlapping action proposals.
"""

from typing import Any, Dict, List, Set
from app.agents.state import CAPAWorkflowState
from app.core.logging import get_logger
from app.schemas.capa import CAPARecommendation, CAPAStatusEnum, CAPATypeEnum

logger = get_logger("agents.nodes.capa_validation")


def capa_validation_node(state: CAPAWorkflowState) -> Dict[str, Any]:
    """Execute quality and regulatory validation across generated CAPA recommendations."""
    logger.info("Executing CAPAValidationNode for workflow %s", state.get("workflow_id"))

    recommendations: List[CAPARecommendation] = list(state.get("capa_recommendations") or [])
    potential_root_causes = state.get("potential_root_causes") or []
    contributing_factors = state.get("contributing_factors") or []
    capa_warnings: List[str] = list(state.get("capa_warnings") or [])

    validation_errors: List[str] = []
    valid_cause_ids: Set[str] = {c.cause_id for c in potential_root_causes if hasattr(c, "cause_id")}
    valid_factor_ids: Set[str] = {f.factor_id for f in contributing_factors if hasattr(f, "factor_id")}
    all_valid_cause_identifiers = valid_cause_ids.union(valid_factor_ids)

    seen_descriptions: List[str] = []

    for idx, rec in enumerate(recommendations):
        prefix = f"Recommendation #{idx+1} ({rec.capa_id}):"

        # 1. Action type validation
        if rec.action_type not in (CAPATypeEnum.CORRECTIVE_ACTION, CAPATypeEnum.PREVENTIVE_ACTION):
            validation_errors.append(f"{prefix} Invalid action_type '{rec.action_type}'. Must be Corrective Action or Preventive Action.")

        # 2. Description validation
        desc_clean = rec.description.strip() if rec.description else ""
        if len(desc_clean) < 10:
            validation_errors.append(f"{prefix} Description must be at least 10 characters detailing actionable remediation steps.")

        # Flag generic recommendations
        lower_desc = desc_clean.lower()
        if any(generic_phrase in lower_desc for generic_phrase in [
            "retrain operator", "retrain all staff", "remind team to be careful", "tell operator to follow sop"
        ]) and len(rec.rationale) < 20:
            capa_warnings.append(
                f"{prefix} Recommendation appears to suggest generic training without detailed procedural root-cause justification."
            )

        # 3. Cause linkage validation
        if rec.related_root_cause_id:
            cause_ref = rec.related_root_cause_id.strip()
            if all_valid_cause_identifiers and cause_ref not in all_valid_cause_identifiers:
                capa_warnings.append(
                    f"{prefix} Referenced root cause ID '{cause_ref}' was not found among validated candidate causes {list(all_valid_cause_identifiers)}."
                )

        # 4. Rationale validation
        if not rec.rationale or len(rec.rationale.strip()) < 5:
            validation_errors.append(f"{prefix} Must provide a clear technical rationale explaining how this action eliminates the failure mode.")

        # 5. Suggested owner role validation
        if not rec.suggested_owner_role or len(rec.suggested_owner_role.strip()) < 2:
            validation_errors.append(f"{prefix} Must specify a suggested owner role (e.g. Senior Maintenance Engineer).")

        # 6. Effectiveness verification validation
        eff = rec.effectiveness_verification
        if not eff:
            validation_errors.append(f"{prefix} Missing mandatory effectiveness verification plan.")
        else:
            if not eff.measurable_outcome or len(eff.measurable_outcome.strip()) < 5:
                validation_errors.append(f"{prefix} Effectiveness verification must define a specific measurable outcome.")
            if not eff.verification_method or len(eff.verification_method.strip()) < 5:
                validation_errors.append(f"{prefix} Effectiveness verification must specify verification method.")
            if not eff.evidence_required or len(eff.evidence_required.strip()) < 5:
                validation_errors.append(f"{prefix} Effectiveness verification must specify required documentary evidence.")
            if not eff.suggested_verifier_role or len(eff.suggested_verifier_role.strip()) < 2:
                validation_errors.append(f"{prefix} Effectiveness verification must specify a suggested verifier role.")
            if not eff.verification_timeframe or len(eff.verification_timeframe.strip()) < 3:
                validation_errors.append(f"{prefix} Effectiveness verification must define evaluation timeframe.")
            if not eff.failure_criteria or len(eff.failure_criteria.strip()) < 5:
                validation_errors.append(f"{prefix} Effectiveness verification must define explicit failure criteria.")

        # 7. Status gate validation: New recommendations cannot be pre-approved
        if rec.review_status in (CAPAStatusEnum.APPROVED, CAPAStatusEnum.COMPLETED, CAPAStatusEnum.CLOSED):
            validation_errors.append(
                f"{prefix} GxP Violation: Generated CAPA recommendation cannot be submitted in '{rec.review_status.value}' status without human QA sign-off."
            )
            # Reset to PENDING_REVIEW
            rec.review_status = CAPAStatusEnum.PENDING_REVIEW

        # 8. Duplicate detection
        for prev_desc in seen_descriptions:
            if desc_clean.lower() == prev_desc.lower():
                capa_warnings.append(f"{prefix} Duplicate action description detected matching another proposed recommendation.")
                break
            # Simple substring / substantial overlap check
            if len(desc_clean) > 20 and len(prev_desc) > 20:
                if desc_clean[:40].lower() == prev_desc[:40].lower():
                    capa_warnings.append(f"{prefix} High similarity/overlap detected with another proposed recommendation.")
                    break

        seen_descriptions.append(desc_clean)

    logger.info(
        "CAPA validation completed with %d errors and %d warnings across %d recommendations",
        len(validation_errors),
        len(capa_warnings),
        len(recommendations),
    )

    return {
        "capa_validation_errors": validation_errors,
        "capa_warnings": capa_warnings,
        "capa_recommendations": recommendations,
    }
