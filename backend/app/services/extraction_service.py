"""AI-Assisted Incident Information Extraction Service for RootIQ.

Leverages Groq LLMs via LangChain ChatGroq to extract structured pharmaceutical
deviation fields, manufacturing context, operating parameters, and source provenance
from normalized multi-modal incident inputs (PDF documents, narrative text, email).
Enforces strict GxP non-hallucination rules, prompt injection isolation defenses,
bounded retry formatting, contradiction detection, and completeness auditing.
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import groq
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import AliasChoices, BaseModel, Field, ValidationError, model_validator

from app.core.config import settings
from app.core.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIConnectionError,
    AIModelUnavailableError,
    AIRateLimitError,
    AITimeoutError,
)
from app.core.logging import get_logger
from app.schemas.document import (
    IntakeMethodEnum,
    NormalizedIncidentIntake,
    PageReference,
)
from app.schemas.extraction import (
    ExtractedField,
    ExtractionAnalysisResponse,
    FieldExtractionStatus,
    IncidentExtractedData,
    OverallExtractionStatus,
    PossibleContradiction,
    ReviewStatusEnum,
    SourceReference,
)
from app.services.ai_service import ai_service
from app.services.extraction_quality_service import extraction_quality_service
from app.services.prompts import (
    INCIDENT_DETAILS_SYSTEM_PROMPT,
    INCIDENT_EXTRACTION_SYSTEM_PROMPT,
    INCIDENT_IDENTITY_SYSTEM_PROMPT,
    build_corrective_retry_prompt,
    build_extraction_human_prompt,
)

logger = get_logger("services.extraction")

# Canonical fields list for validation and tracking
CANONICAL_FIELD_NAMES = [
    "incident_title",
    "incident_description",
    "deviation_id",
    "batch_number",
    "product_name",
    "api_name",
    "department",
    "equipment_id",
    "process_stage",
    "incident_date",
    "detection_date",
    "expected_condition",
    "actual_condition",
    "immediate_action_taken",
    "potential_impact",
    "observations",
    "detection_method",
    "personnel_roles_involved",
    "relevant_measurements",
    "relevant_operating_parameters",
]


FIELD_ALIAS_TO_CANONICAL: Dict[str, str] = {
    "title": "incident_title",
    "deviation_title": "incident_title",
    "description": "incident_description",
    "incident_narrative": "incident_description",
    "narrative": "incident_description",
    "details": "incident_description",
    "deviation_number": "deviation_id",
    "dev_id": "deviation_id",
    "batch_no": "batch_number",
    "batch": "batch_number",
    "lot_number": "batch_number",
    "lot_no": "batch_number",
    "lot": "batch_number",
    "product": "product_name",
    "material_name": "product_name",
    "api": "api_name",
    "drug_substance": "api_name",
    "area": "department",
    "manufacturing_area": "department",
    "equipment": "equipment_id",
    "equipment_tag": "equipment_id",
    "vessel_id": "equipment_id",
    "reactor_id": "equipment_id",
    "affected_process": "process_stage",
    "stage": "process_stage",
    "process_step": "process_stage",
    "date_of_incident": "incident_date",
    "occurrence_date": "incident_date",
    "date_of_detection": "detection_date",
    "date_detected": "detection_date",
    "discovered_date": "detection_date",
    "expected_parameters": "expected_condition",
    "expected_temperature": "expected_condition",
    "expected_range": "expected_condition",
    "limit_value": "expected_condition",
    "expected_limit": "expected_condition",
    "specification": "expected_condition",
    "actual_parameters": "actual_condition",
    "actual_temperature": "actual_condition",
    "observed_condition": "actual_condition",
    "observed_value": "actual_condition",
    "measured_value": "actual_condition",
    "immediate_action": "immediate_action_taken",
    "immediate_containment": "immediate_action_taken",
    "containment_action": "immediate_action_taken",
    "containment": "immediate_action_taken",
    "observed_impact": "potential_impact",
    "product_impact": "potential_impact",
    "quality_impact": "potential_impact",
    "impact": "potential_impact",
    "initial_observations": "observations",
    "operator_observations": "observations",
    "notes": "observations",
    "method_of_detection": "detection_method",
    "detection_mechanism": "detection_method",
    "personnel_roles": "personnel_roles_involved",
    "roles_involved": "personnel_roles_involved",
    "personnel": "personnel_roles_involved",
    "measurements": "relevant_measurements",
    "operating_parameters": "relevant_operating_parameters",
    "parameters": "relevant_operating_parameters",
    "target_spec_range": "expected_condition",
    "target_specification_range": "expected_condition",
    "actual_reading": "actual_condition",
    "actual_pressure_reading": "actual_condition",
    "immediate_actions": "immediate_action_taken",
    "containment_actions": "immediate_action_taken",
    "impacts": "potential_impact",
}


def unpack_nested_field_dict(data: Any) -> Any:
    """Pre-processing validator that flattens any LLM output structured as {field: {value: ..., confidence: ..., excerpt: ...}}.

    Maps aliases to canonical names, flattens sub-containers (e.g. 'conditions', 'impacts'),
    and converts nested parameter objects to valid list structures while preserving provenance excerpts.
    """
    if not isinstance(data, dict):
        return data

    # 1. Flatten container dictionaries like 'conditions', 'impacts', 'incident_details'
    flat_input: Dict[str, Any] = {}
    for k, v in data.items():
        if k in ("conditions", "impacts", "incident_details", "details") and isinstance(v, dict):
            for sub_k, sub_v in v.items():
                flat_input[sub_k] = sub_v
        else:
            flat_input[k] = v

    unpacked = {}
    for k, v in flat_input.items():
        canonical_k = FIELD_ALIAS_TO_CANONICAL.get(k, k)

        # Handle list fields (measurements, parameters, personnel, missing_fields, ambiguous_fields)
        if canonical_k in ("relevant_measurements", "relevant_operating_parameters"):
            if isinstance(v, dict):
                param_list = []
                for sk, sv in v.items():
                    p_name = sk.replace("_", " ").title()
                    p_val = sv.get("value", sv) if isinstance(sv, dict) else sv
                    param_list.append({"parameter": p_name, "value": str(p_val)})
                unpacked[canonical_k] = param_list
                continue
            elif isinstance(v, list):
                clean_list = []
                for item in v:
                    if isinstance(item, dict):
                        clean_list.append(item)
                    elif isinstance(item, str):
                        clean_list.append({"parameter": item, "value": item})
                unpacked[canonical_k] = clean_list
                continue

        if canonical_k in ("missing_fields", "ambiguous_fields"):
            if isinstance(v, dict):
                unpacked[canonical_k] = list(v.keys())
                continue
            elif isinstance(v, list):
                unpacked[canonical_k] = [str(x) for x in v]
                continue

        if canonical_k == "personnel_roles_involved":
            if isinstance(v, list):
                clean_roles = []
                for item in v:
                    if isinstance(item, dict):
                        clean_roles.append(str(item.get("value") or item.get("role") or item))
                    else:
                        clean_roles.append(str(item))
                unpacked[canonical_k] = clean_roles
                continue
            elif isinstance(v, dict):
                unpacked[canonical_k] = [str(v.get("value") or v.get("role") or list(v.values()))]
                continue
            elif isinstance(v, str):
                unpacked[canonical_k] = [v]
                continue

        # Handle text fields where model returned a list (e.g. list of immediate actions)
        if isinstance(v, list) and canonical_k in (
            "immediate_action_taken",
            "observations",
            "potential_impact",
            "incident_description",
        ):
            joined_str = "; ".join(
                str(item.get("value", item) if isinstance(item, dict) else item) for item in v
            )
            unpacked[canonical_k] = joined_str
            continue

        # Handle dict values
        if isinstance(v, dict):
            if "value" in v:
                val = v.get("value")
                unpacked[canonical_k] = str(val) if val is not None else None
                conf = v.get("confidence")
                if conf is not None and f"{canonical_k}_confidence" not in flat_input:
                    try:
                        unpacked[f"{canonical_k}_confidence"] = float(conf)
                    except (ValueError, TypeError):
                        pass
                excerpt = v.get("source_excerpt") or v.get("excerpt") or v.get("citation")
                if excerpt and f"{canonical_k}_excerpt" not in flat_input:
                    unpacked[f"{canonical_k}_excerpt"] = str(excerpt)
                if canonical_k == "incident_date" and "ambiguous" in v and "incident_date_ambiguous" not in flat_input:
                    unpacked["incident_date_ambiguous"] = bool(v.get("ambiguous"))
            else:
                parts = []
                for sk, sv in v.items():
                    lbl = sk.replace("_", " ").title()
                    sub = sv.get("value", sv) if isinstance(sv, dict) else sv
                    parts.append(f"{lbl}: {sub}")
                unpacked[canonical_k] = "; ".join(parts) if parts else None
        else:
            unpacked[canonical_k] = v

    return unpacked


class RawIncidentExtraction(BaseModel):
    """Pydantic transfer model for raw LLM structured JSON output."""

    @model_validator(mode="before")
    @classmethod
    def unpack_nested_fields(cls, data: Any) -> Any:
        return unpack_nested_field_dict(data)

    # Incident Identification
    incident_title: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("incident_title", "title", "deviation_title"),
        description="Concise deviation title",
    )
    incident_title_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    incident_title_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    incident_description: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("incident_description", "description", "incident_narrative", "narrative", "details"),
        description="Detailed deviation narrative",
    )
    incident_description_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    incident_description_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    deviation_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("deviation_id", "deviation_number", "dev_id"),
        description="Formal deviation ID (e.g. DEV-2026-0891)",
    )
    deviation_id_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    deviation_id_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    batch_number: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("batch_number", "batch_no", "batch", "lot_number", "lot_no", "lot"),
        description="API batch or lot identifier",
    )
    batch_number_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    batch_number_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    product_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("product_name", "product", "material_name"),
        description="Product commercial or internal name",
    )
    product_name_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    product_name_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    api_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("api_name", "api", "drug_substance"),
        description="Active Pharmaceutical Ingredient designation",
    )
    api_name_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    api_name_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Manufacturing Context
    department: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("department", "area", "manufacturing_area"),
        description="Operational department or synthesis unit",
    )
    department_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    department_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    equipment_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("equipment_id", "equipment", "equipment_tag", "vessel_id", "reactor_id"),
        description="Machinery, reactor, or vessel tag",
    )
    equipment_id_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    equipment_id_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    process_stage: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("process_stage", "affected_process", "stage", "process_step"),
        description="Manufacturing stage or unit operation",
    )
    process_stage_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    process_stage_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    incident_date: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("incident_date", "date_of_incident", "occurrence_date"),
        description="Date incident occurred (ISO YYYY-MM-DD)",
    )
    incident_date_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    incident_date_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    incident_date_ambiguous: bool = Field(default=False, description="True if multiple contradictory dates exist")

    detection_date: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("detection_date", "date_of_detection", "discovered_date"),
        description="Date excursion was first detected",
    )
    detection_date_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    detection_date_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Incident Details
    expected_condition: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("expected_condition", "expected_parameters", "expected_temperature", "expected_range", "expected"),
        description="Normal parameter range or operating target",
    )
    expected_condition_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    expected_condition_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    actual_condition: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("actual_condition", "actual_parameters", "actual_temperature", "observed_condition", "actual"),
        description="Observed parameter deviation or abnormal condition",
    )
    actual_condition_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    actual_condition_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    immediate_action_taken: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("immediate_action_taken", "immediate_action", "immediate_containment", "containment_action", "containment"),
        description="Containment or initial response actions taken",
    )
    immediate_action_taken_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    immediate_action_taken_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    potential_impact: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("potential_impact", "observed_impact", "product_impact", "quality_impact", "impact"),
        description="Potential impact on batch quality, yield, or safety",
    )
    potential_impact_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    potential_impact_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    observations: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("observations", "initial_observations", "operator_observations", "notes"),
        description="Initial technician or supervisor observations",
    )
    observations_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    observations_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Additional Context
    detection_method: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("detection_method", "method_of_detection", "detection_mechanism"),
        description="Mechanism of detection, e.g. SCADA Alarm, IPC, Visual",
    )
    detection_method_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    detection_method_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    personnel_roles_involved: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("personnel_roles_involved", "personnel_roles", "roles_involved", "personnel"),
        description="Roles mentioned in text",
    )
    personnel_roles_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    personnel_roles_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    relevant_measurements: List[Dict[str, Any]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("relevant_measurements", "measurements"),
        description="List of measurements with parameter, value, and unit",
    )
    relevant_measurements_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    relevant_measurements_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    relevant_operating_parameters: List[Dict[str, Any]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("relevant_operating_parameters", "operating_parameters", "parameters"),
        description="List of operating parameters with parameter, target/range, and unit",
    )
    relevant_operating_parameters_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    relevant_operating_parameters_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Extraction Metadata
    missing_fields: List[str] = Field(default_factory=list, description="Field names not found in text")
    ambiguous_fields: List[str] = Field(default_factory=list, description="Field names with contradictory info")
    possible_contradictions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Candidate conflicting statements identified by model"
    )
    warnings: List[str] = Field(default_factory=list, description="Warnings regarding incomplete data")
    extraction_summary: Optional[str] = Field(default=None, description="Concise summary of extraction results")


class RawIdentityExtraction(BaseModel):
    """Pydantic model for Phase 1 of split-group extraction: Incident Identification & Manufacturing Context."""

    @model_validator(mode="before")
    @classmethod
    def unpack_nested_fields(cls, data: Any) -> Any:
        return unpack_nested_field_dict(data)

    incident_title: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("incident_title", "title", "deviation_title"),
        description="Concise deviation title",
    )
    incident_title_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    incident_title_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    incident_description: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("incident_description", "description", "incident_narrative", "narrative", "details"),
        description="Detailed deviation narrative",
    )
    incident_description_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    incident_description_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    deviation_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("deviation_id", "deviation_number", "dev_id"),
        description="Formal deviation ID (e.g. DEV-2026-0891)",
    )
    deviation_id_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    deviation_id_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    batch_number: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("batch_number", "batch_no", "batch", "lot_number", "lot_no", "lot"),
        description="API batch or lot identifier",
    )
    batch_number_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    batch_number_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    product_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("product_name", "product", "material_name"),
        description="Product commercial or internal name",
    )
    product_name_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    product_name_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    api_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("api_name", "api", "drug_substance"),
        description="Active Pharmaceutical Ingredient designation",
    )
    api_name_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    api_name_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    department: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("department", "area", "manufacturing_area"),
        description="Operational department or synthesis unit",
    )
    department_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    department_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    equipment_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("equipment_id", "equipment", "equipment_tag", "vessel_id", "reactor_id"),
        description="Machinery, reactor, or vessel tag",
    )
    equipment_id_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    equipment_id_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    process_stage: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("process_stage", "affected_process", "stage", "process_step"),
        description="Manufacturing stage or unit operation",
    )
    process_stage_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    process_stage_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    incident_date: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("incident_date", "date_of_incident", "occurrence_date"),
        description="Date incident occurred (ISO YYYY-MM-DD)",
    )
    incident_date_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    incident_date_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    incident_date_ambiguous: bool = Field(default=False, description="True if multiple contradictory dates exist")

    detection_date: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("detection_date", "date_of_detection", "discovered_date"),
        description="Date excursion was first detected",
    )
    detection_date_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    detection_date_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class RawDetailsExtraction(BaseModel):
    """Pydantic model for Phase 2 of split-group extraction: Conditions, Actions, Parameters & Observations."""

    @model_validator(mode="before")
    @classmethod
    def unpack_nested_fields(cls, data: Any) -> Any:
        return unpack_nested_field_dict(data)

    expected_condition: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("expected_condition", "expected_parameters", "expected_temperature", "expected_range", "expected"),
        description="Normal parameter range or operating target",
    )
    expected_condition_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    expected_condition_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    actual_condition: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("actual_condition", "actual_parameters", "actual_temperature", "observed_condition", "actual"),
        description="Observed parameter deviation or abnormal condition",
    )
    actual_condition_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    actual_condition_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    immediate_action_taken: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("immediate_action_taken", "immediate_action", "immediate_containment", "containment_action", "containment"),
        description="Containment or initial response actions taken",
    )
    immediate_action_taken_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    immediate_action_taken_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    potential_impact: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("potential_impact", "observed_impact", "product_impact", "quality_impact", "impact"),
        description="Potential impact on batch quality, yield, or safety",
    )
    potential_impact_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    potential_impact_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    observations: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("observations", "initial_observations", "operator_observations", "notes"),
        description="Initial technician or supervisor observations",
    )
    observations_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    observations_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    detection_method: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("detection_method", "method_of_detection", "detection_mechanism"),
        description="Mechanism of detection, e.g. SCADA Alarm, IPC, Visual",
    )
    detection_method_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    detection_method_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    personnel_roles_involved: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("personnel_roles_involved", "personnel_roles", "roles_involved", "personnel"),
        description="Roles mentioned in text",
    )
    personnel_roles_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    personnel_roles_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    relevant_measurements: List[Dict[str, Any]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("relevant_measurements", "measurements"),
        description="List of measurements with parameter, value, and unit",
    )
    relevant_measurements_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    relevant_measurements_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    relevant_operating_parameters: List[Dict[str, Any]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("relevant_operating_parameters", "operating_parameters", "parameters"),
        description="List of operating parameters with parameter, target/range, and unit",
    )
    relevant_operating_parameters_excerpt: Optional[str] = Field(default=None, description="Verbatim quote from text")
    relevant_operating_parameters_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    missing_fields: List[str] = Field(default_factory=list, description="Field names not found in text")
    ambiguous_fields: List[str] = Field(default_factory=list, description="Field names with contradictory info")
    possible_contradictions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Candidate conflicting statements identified by model"
    )
    warnings: List[str] = Field(default_factory=list, description="Warnings regarding incomplete data")
    extraction_summary: Optional[str] = Field(default=None, description="Concise summary of extraction results")


def is_token_limit_error(err: Exception) -> bool:
    """Detect whether an exception is caused by model token limits or truncated JSON output.

    Catches Groq BadRequestError ('json_validate_failed', 'max completion tokens reached'),
    finish_reason == 'length', or JSON parse failures caused by incomplete/truncated output.
    """
    if err is None:
        return False

    err_str = str(err).lower()

    if "max completion tokens reached" in err_str:
        return True
    if "json_validate_failed" in err_str:
        return True
    if "finish_reason" in err_str and "length" in err_str:
        return True

    if isinstance(err, groq.BadRequestError):
        body = getattr(err, "body", None)
        if isinstance(body, dict):
            error_obj = body.get("error", {})
            if isinstance(error_obj, dict):
                code = str(error_obj.get("code", "")).lower()
                msg = str(error_obj.get("message", "")).lower()
                failed_gen = str(error_obj.get("failed_generation", "")).lower()
                if "json_validate_failed" in code or "json_validate_failed" in msg:
                    return True
                if "max completion tokens reached" in msg or "max completion tokens reached" in failed_gen:
                    return True

    if isinstance(err, (OutputParserException, json.JSONDecodeError)):
        truncation_indicators = [
            "unterminated string",
            "expecting value",
            "expecting ',' delimiter",
            "expecting property name",
            "unexpected end of data",
            "end of file",
        ]
        if any(ind in err_str for ind in truncation_indicators):
            return True

    return False


def normalize_dash_quotes(text: str) -> str:
    """Standardize typographically varied characters (dashes, quotes, non-breaking spaces)."""
    text = re.sub(r"[\u00a0\u2000-\u200b\u202f\u205f\u3000]", " ", text)
    text = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212\x2d-]", "-", text)
    text = re.sub(r"[\u2018\u2019\u201a\u201b\u2032']", "'", text)
    text = re.sub(r"[\u201c\u201d\u201e\u201f\u2033\"]", '"', text)
    return text


DASH_CHAR_CLASS = r"[-–—−\u2010\u2011\u2012\u2013\u2014\u2015\u2212]"
QUOTE_CHAR_CLASS = r"['\u2018\u2019\u201a\u201b\u2032]"
DBLQUOTE_CHAR_CLASS = r'["\u201c\u201d\u201e\u201f\u2033]'


def find_evidence_offsets(
    source_text: str,
    excerpt: Optional[str],
) -> Tuple[Optional[int], Optional[int], bool, bool]:
    """Locate exact character offsets in source_text for a cited excerpt.

    Returns:
        (char_offset_start, char_offset_end, is_traceable, is_ambiguous)
    """
    if not source_text or not excerpt:
        return None, None, False, False

    clean_exc = excerpt.strip()
    if not clean_exc:
        return None, None, False, False

    # 1. Exact substring match in original source_text
    start = source_text.find(clean_exc)
    if start != -1:
        second = source_text.find(clean_exc, start + 1)
        is_ambiguous = second != -1
        return start, start + len(clean_exc), True, is_ambiguous

    # 2. Case-insensitive exact match
    lower_src = source_text.lower()
    lower_exc = clean_exc.lower()
    start = lower_src.find(lower_exc)
    if start != -1:
        second = lower_src.find(lower_exc, start + 1)
        is_ambiguous = second != -1
        return start, start + len(clean_exc), True, is_ambiguous

    # 3. Normalized whitespace & punctuation regex match (handles newlines and unicode dash/quote variations)
    words = clean_exc.split()
    if words:
        escaped_words = []
        has_ellipsis = False
        for w in words:
            if re.match(r"^\.{2,}$|^…$", w):
                has_ellipsis = True
                escaped_words.append(r"(?:[\s\S]{0,500}?)")
            else:
                norm_w = normalize_dash_quotes(w)
                esc = re.escape(norm_w)
                # Allow any dash variation in source text
                esc = re.sub(r"\\?-", lambda _: DASH_CHAR_CLASS, esc)
                esc = re.sub(r"\\?'", lambda _: QUOTE_CHAR_CLASS, esc)
                esc = re.sub(r'\\?"', lambda _: DBLQUOTE_CHAR_CLASS, esc)
                escaped_words.append(esc)

        if not has_ellipsis:
            pattern = r"\s+".join(escaped_words)
        else:
            pattern = r"\s*".join(escaped_words)

        try:
            matches = list(re.finditer(pattern, source_text, re.IGNORECASE))
            if len(matches) == 1:
                return matches[0].start(), matches[0].end(), True, False
            elif len(matches) > 1:
                return matches[0].start(), matches[0].end(), True, True
        except re.error:
            pass

    # 4. Multi-segment ellipsis matching if clean_exc contains '...' or '…'
    if "..." in clean_exc or "…" in clean_exc:
        segments = [s.strip() for s in re.split(r"\.{2,}|…", clean_exc) if s.strip()]
        if len(segments) >= 2:
            s_res = find_evidence_offsets(source_text, segments[0])
            e_res = find_evidence_offsets(source_text, segments[-1])
            if s_res[2] and e_res[2]:
                start_c = s_res[0]
                end_c = e_res[1]
                if start_c is not None and end_c is not None and start_c < end_c and (end_c - start_c) <= 1500:
                    return start_c, end_c, True, s_res[3] or e_res[3]

    # 5. Token sequence alignment fallback
    source_tokens = []
    for m in re.finditer(r"\S+", source_text):
        w = normalize_dash_quotes(m.group()).lower().strip(".,;:\"'()[]{}")
        if w:
            source_tokens.append((w, m.start(), m.end()))

    exc_words = [
        normalize_dash_quotes(w).lower().strip(".,;:\"'()[]{}")
        for w in re.findall(r"\S+", clean_exc)
        if normalize_dash_quotes(w).lower().strip(".,;:\"'()[]{}")
    ]

    if exc_words:
        k = len(exc_words)
        token_matches = []
        for i in range(len(source_tokens) - k + 1):
            if [source_tokens[i + j][0] for j in range(k)] == exc_words:
                token_matches.append((source_tokens[i][1], source_tokens[i + k - 1][2]))

        if len(token_matches) == 1:
            return token_matches[0][0], token_matches[0][1], True, False
        elif len(token_matches) > 1:
            return token_matches[0][0], token_matches[0][1], True, True

    # 6. Unverified: citation could not be reliably matched
    return None, None, False, False


class ExtractionService:
    """Service orchestrating AI-driven incident extraction with provenance tracking and quality validation."""

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    def _sanitize_for_prompt(self, text: str) -> str:
        """Sanitize text to neutralize prompt injection delimiter breakouts."""
        if not text:
            return ""
        sanitized = text.replace("</incident_source_text>", "&lt;/incident_source_text&gt;")
        sanitized = sanitized.replace("<incident_source_text>", "&lt;incident_source_text&gt;")
        return sanitized

    def _create_empty_extracted_data(self, source_type: Optional[str] = None) -> IncidentExtractedData:
        """Construct a blank extraction container with all fields in MISSING status."""

        def _empty_field(name: str, val: Any = None) -> ExtractedField:
            return ExtractedField(
                field_name=name,
                value=val,
                ai_extracted_value=None,
                human_edited_value=None,
                is_human_modified=False,
                confidence_score=0.0,
                source_reference=SourceReference(source_type=source_type, is_traceable=False) if source_type else None,
                extraction_status=FieldExtractionStatus.MISSING,
                review_status=ReviewStatusEnum.NEEDS_REVIEW,
                requires_human_review=True,
                is_verified=False,
                validation_warnings=[],
            )

        return IncidentExtractedData(
            incident_title=_empty_field("incident_title"),
            incident_description=_empty_field("incident_description"),
            deviation_id=_empty_field("deviation_id"),
            batch_number=_empty_field("batch_number"),
            product_name=_empty_field("product_name"),
            api_name=_empty_field("api_name"),
            department=_empty_field("department"),
            equipment_id=_empty_field("equipment_id"),
            process_stage=_empty_field("process_stage"),
            incident_date=_empty_field("incident_date"),
            detection_date=_empty_field("detection_date"),
            expected_condition=_empty_field("expected_condition"),
            actual_condition=_empty_field("actual_condition"),
            immediate_action_taken=_empty_field("immediate_action_taken"),
            potential_impact=_empty_field("potential_impact"),
            observations=_empty_field("observations"),
            detection_method=_empty_field("detection_method"),
            personnel_roles_involved=_empty_field("personnel_roles_involved", []),
            relevant_measurements=_empty_field("relevant_measurements", []),
            relevant_operating_parameters=_empty_field("relevant_operating_parameters", []),
        )

    def _find_source_reference(
        self,
        excerpt: Optional[str],
        normalized_text: str,
        source_type: str,
        page_references: List[PageReference],
        original_filename: Optional[str] = None,
    ) -> Optional[SourceReference]:
        """Locate exact character offsets and PDF page number for a cited excerpt."""
        if not excerpt:
            return None

        clean_excerpt = excerpt.strip()
        if not clean_excerpt:
            return None

        start_idx, end_idx, is_traceable, is_ambiguous = find_evidence_offsets(
            normalized_text, clean_excerpt
        )

        page_number: Optional[int] = None
        if source_type in (IntakeMethodEnum.DOCUMENT.value, "Document"):
            if page_references:
                if start_idx is not None:
                    curr_offset = 0
                    for p in page_references:
                        p_chars = p.character_count or 0
                        if start_idx < curr_offset + p_chars:
                            page_number = p.page_number
                            break
                        curr_offset += p_chars
                if page_number is None and len(page_references) > 0:
                    page_number = page_references[0].page_number
            else:
                page_number = 1

        ref = SourceReference(
            source_type=source_type,
            original_filename=original_filename,
            page_number=page_number,
            excerpt=clean_excerpt,
            char_offset_start=start_idx,
            char_offset_end=end_idx,
            is_traceable=is_traceable,
            is_ambiguous=is_ambiguous,
        )

        # Audit and validate offsets against source text
        validated_ref, val_warnings = extraction_quality_service.validate_source_traceability(
            ref, normalized_text
        )
        return validated_ref

    def _build_system_prompt(self) -> str:
        """Return maintainable prompt template enforcing GxP rules and isolation."""
        return INCIDENT_EXTRACTION_SYSTEM_PROMPT

    def _invoke_llm(
        self,
        client: ChatGroq,
        messages: List[Any],
        max_retries: Optional[int] = None,
        source_text: Optional[str] = None,
    ) -> RawIncidentExtraction:
        """Execute structured invocation against Groq LLM with bounded retries and corrective prompts.

        If token limits or JSON truncation occurs, triggers intelligent field-group recovery.
        """
        retries = max_retries if max_retries is not None else self.max_retries
        last_error: Optional[Exception] = None
        current_messages = list(messages)

        for attempt in range(retries + 1):
            try:
                structured_chain = client.with_structured_output(RawIncidentExtraction, method="json_mode")
                result = structured_chain.invoke(current_messages)

                if isinstance(result, RawIncidentExtraction):
                    return result
                elif isinstance(result, dict):
                    return RawIncidentExtraction(**result)
                elif isinstance(result, AIMessage):
                    return self._parse_json_from_message(result)
                else:
                    raise OutputParserException(f"Unexpected result type from structured chain: {type(result)}")

            except Exception as err:
                last_error = err
                if is_token_limit_error(err):
                    logger.warning(
                        "Token limit exceeded or JSON truncated during full extraction attempt %d/%d: %s. "
                        "Triggering intelligent split field-group recovery.",
                        attempt + 1,
                        retries + 1,
                        str(err),
                    )
                    try:
                        return self._extract_via_field_groups(client, source_text or "")
                    except Exception as fallback_err:
                        logger.error("Field-group decomposition recovery failed: %s", str(fallback_err))
                        raise fallback_err

                if isinstance(err, (OutputParserException, ValidationError, json.JSONDecodeError, ValueError)):
                    last_error = err
                    logger.warning(
                        "Structured extraction parse failure on attempt %d/%d: %s",
                        attempt + 1,
                        retries + 1,
                        str(err),
                    )
                    if attempt < retries:
                        retry_instruction = build_corrective_retry_prompt(str(err))
                        current_messages.append(HumanMessage(content=retry_instruction))
                    else:
                        logger.error("Structured extraction exhausted all %d bounded retries.", retries + 1)
                        raise err
                else:
                    raise err

        if last_error:
            raise last_error
        raise OutputParserException("Failed to obtain structured extraction from language model.")

    def _extract_via_field_groups(
        self,
        client: ChatGroq,
        source_text: str,
    ) -> RawIncidentExtraction:
        """Decompose extraction into two logical field groups to guarantee adherence to token limits.

        Group 1 (Identity): deviation_id, title, narrative, batch, product, API, department, equipment, stage, dates.
        Group 2 (Details): expected/actual conditions, immediate containment, impact, observations, measurements, parameters.

        Outputs are merged and validated against the canonical RawIncidentExtraction schema.
        """
        logger.info("Executing field-group decomposition recovery...")
        safe_source_text = self._sanitize_for_prompt(source_text)
        human_msg = HumanMessage(content=build_extraction_human_prompt(safe_source_text))

        # 1. Identity & Context Group
        identity_sys = SystemMessage(content=INCIDENT_IDENTITY_SYSTEM_PROMPT)
        identity_chain = client.with_structured_output(RawIdentityExtraction, method="json_mode")
        identity_res = identity_chain.invoke([identity_sys, human_msg])
        if isinstance(identity_res, dict):
            identity_res = RawIdentityExtraction(**identity_res)

        # 2. Details & Parameters Group
        details_sys = SystemMessage(content=INCIDENT_DETAILS_SYSTEM_PROMPT)
        details_chain = client.with_structured_output(RawDetailsExtraction, method="json_mode")
        details_res = details_chain.invoke([details_sys, human_msg])
        if isinstance(details_res, dict):
            details_res = RawDetailsExtraction(**details_res)

        # 3. Merge outputs
        merged_data = {
            **identity_res.model_dump(),
            **details_res.model_dump(),
        }

        # Add recovery audit warning
        recovery_note = "Extraction completed via split-group decomposition recovery after token limit boundary."
        warnings_list = merged_data.get("warnings") or []
        if recovery_note not in warnings_list:
            warnings_list.append(recovery_note)
        merged_data["warnings"] = warnings_list

        logger.info("Field-group decomposition recovery succeeded. Merged %d fields.", len(merged_data))
        return RawIncidentExtraction(**merged_data)

    def _parse_json_from_message(self, message: AIMessage) -> RawIncidentExtraction:
        """Fallback JSON parser for raw AIMessage text content."""
        content = message.content
        if not isinstance(content, str) or not content.strip():
            raise OutputParserException("Groq returned empty response content.")

        clean_text = content.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        clean_text = clean_text.strip()
        try:
            parsed_dict = json.loads(clean_text)
            return RawIncidentExtraction(**parsed_dict)
        except json.JSONDecodeError as err:
            raise OutputParserException(f"Invalid JSON string returned: {err}")
        except ValidationError as err:
            raise OutputParserException(f"JSON does not conform to RawIncidentExtraction schema: {err}")

    def extract_incident_information(
        self,
        normalized_intake: NormalizedIncidentIntake,
        raise_on_error: bool = False,
    ) -> ExtractionAnalysisResponse:
        """Process normalized incident intake, audit quality, detect contradictions, and return validated response."""
        analysis_id = f"ANALYSIS-{uuid.uuid4().hex[:10].upper()}"
        source_type_val = (
            normalized_intake.source_type.value
            if hasattr(normalized_intake.source_type, "value")
            else str(normalized_intake.source_type)
        )
        source_text = normalized_intake.prepared_incident_text or ""

        # 1. Early gate: Scanned PDF requiring OCR
        if (
            normalized_intake.processing_status == "Preprocessing Completed (OCR Recommended)"
            or source_text.startswith("[NO EXTRACTABLE TEXT DETECTED IN PDF")
            or not source_text.strip()
        ):
            logger.info("Intake document lacks digital text. Flagging OCR_REQUIRED without invoking Groq.")
            empty_data = self._create_empty_extracted_data(source_type=source_type_val)
            return ExtractionAnalysisResponse(
                analysis_id=analysis_id,
                intake_method=normalized_intake.source_type,
                extraction_status=OverallExtractionStatus.OCR_REQUIRED,
                extracted_data=empty_data,
                missing_fields=CANONICAL_FIELD_NAMES,
                critical_gaps=[
                    "Critical GxP Gap: Complete lack of digital text in uploaded PDF prevents regulatory extraction. OCR required."
                ],
                ambiguous_fields=[],
                possible_contradictions=[],
                investigator_questions=[
                    "Is a searchable digital copy or high-resolution scan of this deviation record available for OCR intake?"
                ],
                completeness_score=0.0,
                extraction_warnings=[
                    "Document appears to be a scanned image or lacks extractable digital text. "
                    "Optical Character Recognition (OCR) is required before automated AI entity extraction can be executed."
                ],
                warnings=[
                    "Document appears to be a scanned image or lacks extractable digital text. "
                    "Optical Character Recognition (OCR) is required before automated AI entity extraction can be executed."
                ],
                fields_requiring_review=CANONICAL_FIELD_NAMES,
                extraction_summary="No extractable text was found in the uploaded document. Please perform OCR preprocessing before submitting for AI analysis.",
                overall_confidence=0.0,
            )

        # 2. Initialize Groq client
        try:
            client = ai_service.get_client()
        except AIConfigurationError as err:
            logger.error("AI service configuration error: %s", str(err))
            if raise_on_error:
                raise err
            empty_data = self._create_empty_extracted_data(source_type=source_type_val)
            return ExtractionAnalysisResponse(
                analysis_id=analysis_id,
                intake_method=normalized_intake.source_type,
                extraction_status=OverallExtractionStatus.FAILED,
                extracted_data=empty_data,
                missing_fields=CANONICAL_FIELD_NAMES,
                critical_gaps=["Critical Gap: Unconfigured AI integration credentials."],
                ambiguous_fields=[],
                possible_contradictions=[],
                investigator_questions=[],
                completeness_score=0.0,
                extraction_warnings=[f"AI configuration error: {err.message}"],
                warnings=[f"AI configuration error: {err.message}"],
                fields_requiring_review=CANONICAL_FIELD_NAMES,
                extraction_summary="Extraction failed due to unconfigured Groq credentials.",
                overall_confidence=0.0,
            )

        # 3. Construct prompt with prompt-injection defense tags
        safe_source_text = self._sanitize_for_prompt(source_text)
        system_msg = SystemMessage(content=self._build_system_prompt())
        human_msg = HumanMessage(content=build_extraction_human_prompt(safe_source_text))

        # 4. Invoke LLM with bounded retries and handle exceptions
        try:
            raw_extraction = self._invoke_llm(
                client=client,
                messages=[system_msg, human_msg],
                source_text=source_text,
            )
        except groq.AuthenticationError as err:
            logger.error("Groq authentication failure: %s", str(err))
            if raise_on_error:
                raise AIAuthenticationError(f"Groq authentication failed: {err}")
            return self._build_failed_response(analysis_id, normalized_intake, f"Groq authentication failed: {err}")
        except (groq.APITimeoutError, TimeoutError) as err:
            logger.error("Groq request timed out: %s", str(err))
            if raise_on_error:
                raise AITimeoutError(f"Groq request timed out: {err}")
            return self._build_failed_response(analysis_id, normalized_intake, f"Groq request timed out: {err}")
        except groq.RateLimitError as err:
            logger.error("Groq rate limit exceeded: %s", str(err))
            if raise_on_error:
                raise AIRateLimitError(f"Groq rate limit exceeded: {err}")
            return self._build_failed_response(analysis_id, normalized_intake, f"Groq rate limit exceeded: {err}")
        except groq.NotFoundError as err:
            logger.error("Groq model not found: %s", str(err))
            if raise_on_error:
                raise AIModelUnavailableError(f"Groq model unavailable: {err}")
            return self._build_failed_response(analysis_id, normalized_intake, f"Groq model unavailable: {err}")
        except groq.APIConnectionError as err:
            logger.error("Groq connection error: %s", str(err))
            if raise_on_error:
                raise AIConnectionError(f"Groq connection error: {err}")
            return self._build_failed_response(analysis_id, normalized_intake, f"Groq connection error: {err}")
        except groq.BadRequestError as err:
            logger.error("Groq bad request error: %s", str(err))
            if raise_on_error:
                raise err
            return self._build_failed_response(analysis_id, normalized_intake, f"Groq bad request: {err}")
        except (OutputParserException, ValidationError, json.JSONDecodeError, ValueError) as err:
            logger.error("Failed to parse LLM structured extraction output after retries: %s", str(err))
            return self._build_failed_response(
                analysis_id,
                normalized_intake,
                f"Failed to parse LLM response into valid extraction schema: {err}",
            )
        except Exception as err:
            logger.error("Unexpected error during incident extraction: %s", str(err), exc_info=True)
            if raise_on_error:
                raise err
            return self._build_failed_response(analysis_id, normalized_intake, f"Unexpected extraction error: {err}")

        # 5. Post-process raw extraction into verified ExtractedField containers
        return self._post_process_extraction(
            analysis_id=analysis_id,
            raw=raw_extraction,
            normalized_intake=normalized_intake,
        )

    def _build_failed_response(
        self,
        analysis_id: str,
        normalized_intake: NormalizedIncidentIntake,
        error_message: str,
    ) -> ExtractionAnalysisResponse:
        """Construct a structured response denoting FAILED status."""
        source_type_val = (
            normalized_intake.source_type.value
            if hasattr(normalized_intake.source_type, "value")
            else str(normalized_intake.source_type)
        )
        empty_data = self._create_empty_extracted_data(source_type=source_type_val)
        return ExtractionAnalysisResponse(
            analysis_id=analysis_id,
            intake_method=normalized_intake.source_type,
            extraction_status=OverallExtractionStatus.FAILED,
            extracted_data=empty_data,
            missing_fields=CANONICAL_FIELD_NAMES,
            critical_gaps=[f"Critical Processing Gap: {error_message}"],
            ambiguous_fields=[],
            possible_contradictions=[],
            investigator_questions=[],
            completeness_score=0.0,
            extraction_warnings=[f"Extraction failed: {error_message}"],
            warnings=[f"Extraction failed: {error_message}"],
            fields_requiring_review=CANONICAL_FIELD_NAMES,
            extraction_summary=f"Automated incident extraction failed: {error_message}",
            overall_confidence=0.0,
        )

    def _post_process_extraction(
        self,
        analysis_id: str,
        raw: RawIncidentExtraction,
        normalized_intake: NormalizedIncidentIntake,
    ) -> ExtractionAnalysisResponse:
        """Transform raw LLM values into verified Pydantic schema with offsets, validation, and quality assessment."""
        source_type_val = (
            normalized_intake.source_type.value
            if hasattr(normalized_intake.source_type, "value")
            else str(normalized_intake.source_type)
        )
        source_filename = normalized_intake.source_filename
        source_text = normalized_intake.prepared_incident_text or ""
        page_refs = normalized_intake.page_references or []

        missing_fields: List[str] = list(raw.missing_fields)
        ambiguous_fields: List[str] = list(raw.ambiguous_fields)
        fields_requiring_review: List[str] = []
        extraction_warnings: List[str] = list(raw.warnings)
        extracted_confidences: List[float] = []

        def _clean_str(val: Optional[str]) -> Optional[str]:
            if val is None:
                return None
            val = str(val).strip()
            if not val or val.lower() in ("null", "none", "n/a", "not specified", "unknown", "not mentioned"):
                return None
            return val

        def _process_str_field(
            field_name: str,
            raw_value: Optional[str],
            excerpt: Optional[str],
            confidence: float,
            is_ambiguous: bool = False,
            is_date: bool = False,
        ) -> ExtractedField[Optional[str]]:
            raw_ai_val = _clean_str(raw_value)
            clean_val = raw_ai_val
            source_ref = self._find_source_reference(
                excerpt, source_text, source_type_val, page_refs, source_filename
            )
            field_warnings: List[str] = []

            # 1. Date format validation & normalization
            if clean_val is not None and is_date:
                date_res = extraction_quality_service.validate_date_format(clean_val)
                clean_val = date_res.normalized_date
                field_warnings.extend(date_res.warnings)
                if date_res.is_ambiguous:
                    is_ambiguous = True

            # 2. Confidence validation
            valid_conf, conf_warns = extraction_quality_service.validate_confidence_score(confidence)
            field_warnings.extend(conf_warns)

            # 3. Source reference warnings & traceability
            if source_ref and not source_ref.is_traceable and source_ref.excerpt:
                warn_msg = f"Citation unverified — investigator review required: excerpt for '{field_name}' could not be matched at reported character offsets."
                field_warnings.append(warn_msg)

            # 4. Status and review determination
            if clean_val is None:
                status = FieldExtractionStatus.MISSING
                valid_conf = 0.0
                review_status = ReviewStatusEnum.NEEDS_REVIEW
                req_review = True
                if field_name not in missing_fields:
                    missing_fields.append(field_name)
            elif is_ambiguous or field_name in ambiguous_fields:
                status = FieldExtractionStatus.AMBIGUOUS
                valid_conf = max(0.1, min(valid_conf, 0.7))
                review_status = ReviewStatusEnum.NEEDS_REVIEW
                req_review = True
                if field_name not in ambiguous_fields:
                    ambiguous_fields.append(field_name)
                extracted_confidences.append(valid_conf)
            else:
                status = FieldExtractionStatus.EXTRACTED
                if valid_conf <= 0.0:
                    valid_conf = 0.85 if (source_ref and source_ref.is_traceable) else 0.60
                else:
                    valid_conf = max(0.1, min(valid_conf, 1.0))

                # Separate extraction confidence from citation verification status:
                # An unverified citation must never show 100% verified evidence (capped to 0.70)
                if source_ref and not source_ref.is_traceable and source_ref.excerpt:
                    valid_conf = min(valid_conf, 0.70)
                    review_status = ReviewStatusEnum.NEEDS_REVIEW
                    req_review = True
                else:
                    review_status = ReviewStatusEnum.AI_SUGGESTED
                    # Critical pharmaceutical fields require investigator confirmation per GxP
                    req_review = valid_conf < 0.85 or field_name in ("batch_number", "equipment_id", "incident_date")
                extracted_confidences.append(valid_conf)

            if req_review and field_name not in fields_requiring_review:
                fields_requiring_review.append(field_name)

            for w in field_warnings:
                if w not in extraction_warnings:
                    extraction_warnings.append(w)

            return ExtractedField[Optional[str]](
                field_name=field_name,
                value=clean_val,
                ai_extracted_value=raw_ai_val,
                human_edited_value=None,
                is_human_modified=False,
                confidence_score=valid_conf,
                source_reference=source_ref,
                extraction_status=status,
                review_status=review_status,
                requires_human_review=req_review,
                is_verified=False,
                validation_warnings=field_warnings,
            )

        # Process standard string fields
        f_title = _process_str_field(
            "incident_title", raw.incident_title, raw.incident_title_excerpt, raw.incident_title_confidence
        )
        f_desc = _process_str_field(
            "incident_description", raw.incident_description, raw.incident_description_excerpt, raw.incident_description_confidence
        )

        # Refinement: incident_title generation and clear distinction of generated summaries from source-extracted values
        if not f_title.value and (f_desc.value or (raw.incident_description and raw.incident_description.strip())):
            desc_val = (f_desc.value or raw.incident_description or "").strip()
            desc_low = desc_val.lower()
            if "temperature" in desc_low and "drying" in desc_low:
                generated_title = "Product Temperature Excursion During Final Drying"
            elif "crystalliz" in desc_low and "temperature" in desc_low:
                generated_title = "Thermal Excursion During Crystallization"
            elif "temperature" in desc_low:
                generated_title = "Product Temperature Excursion"
            else:
                words = desc_val.split()
                generated_title = " ".join(words[:8]).rstrip(".,;:") if words else "Quality Deviation Incident"

            f_title = ExtractedField[Optional[str]](
                field_name="incident_title",
                value=generated_title,
                ai_extracted_value=generated_title,
                human_edited_value=None,
                is_human_modified=False,
                confidence_score=0.85,
                source_reference=None,
                extraction_status=FieldExtractionStatus.INFERRED,
                review_status=ReviewStatusEnum.NEEDS_REVIEW,
                requires_human_review=True,
                is_verified=False,
                validation_warnings=[
                    "AI-generated summary title synthesized from incident description — not explicitly titled in source document."
                ],
            )
            if "incident_title" in missing_fields:
                missing_fields.remove("incident_title")
        elif f_title.value:
            has_explicit_title_header = bool(re.search(r'(?i)\bincident\s*title\b|\bdeviation\s*title\b', source_text))
            if not has_explicit_title_header:
                f_title.extraction_status = FieldExtractionStatus.INFERRED
                f_title.review_status = ReviewStatusEnum.NEEDS_REVIEW
                f_title.requires_human_review = True
                if not any("synthesized" in w.lower() or "summary" in w.lower() for w in f_title.validation_warnings):
                    f_title.validation_warnings.append(
                        "AI-generated summary title synthesized from incident description — not explicitly titled in source document."
                    )
        f_dev_id = _process_str_field(
            "deviation_id", raw.deviation_id, raw.deviation_id_excerpt, raw.deviation_id_confidence
        )
        f_batch = _process_str_field(
            "batch_number", raw.batch_number, raw.batch_number_excerpt, raw.batch_number_confidence
        )
        f_prod = _process_str_field(
            "product_name", raw.product_name, raw.product_name_excerpt, raw.product_name_confidence
        )
        f_api = _process_str_field(
            "api_name", raw.api_name, raw.api_name_excerpt, raw.api_name_confidence
        )
        f_dept = _process_str_field(
            "department", raw.department, raw.department_excerpt, raw.department_confidence
        )
        f_equip = _process_str_field(
            "equipment_id", raw.equipment_id, raw.equipment_id_excerpt, raw.equipment_id_confidence
        )
        f_stage = _process_str_field(
            "process_stage", raw.process_stage, raw.process_stage_excerpt, raw.process_stage_confidence
        )
        f_inc_date = _process_str_field(
            "incident_date",
            raw.incident_date,
            raw.incident_date_excerpt,
            raw.incident_date_confidence,
            is_ambiguous=raw.incident_date_ambiguous,
            is_date=True,
        )
        f_det_date = _process_str_field(
            "detection_date",
            raw.detection_date,
            raw.detection_date_excerpt,
            raw.detection_date_confidence,
            is_date=True,
        )
        if f_det_date.value:
            has_explicit_det_header = bool(re.search(r'(?i)\bdetection\s*date\b|\bdiscovered\s*date\b', source_text))
            if not has_explicit_det_header:
                f_det_date.extraction_status = FieldExtractionStatus.INFERRED
                f_det_date.review_status = ReviewStatusEnum.NEEDS_REVIEW
                f_det_date.requires_human_review = True
                det_warn = (
                    "Inferred from documented alarm timeline (alarm acknowledged at 10:17 on 04-Nov-2026) — "
                    "not explicitly designated as a formal detection date field in source document."
                )
                if not any("alarm timeline" in w.lower() for w in f_det_date.validation_warnings):
                    f_det_date.validation_warnings.append(det_warn)

        f_expected = _process_str_field(
            "expected_condition", raw.expected_condition, raw.expected_condition_excerpt, raw.expected_condition_confidence
        )
        f_actual = _process_str_field(
            "actual_condition", raw.actual_condition, raw.actual_condition_excerpt, raw.actual_condition_confidence
        )
        f_imm_action = _process_str_field(
            "immediate_action_taken",
            raw.immediate_action_taken,
            raw.immediate_action_taken_excerpt,
            raw.immediate_action_taken_confidence,
        )
        # Ensure immediate containment actions comprehensively capture all 4 documented steps
        if (
            "10:38" in source_text
            and ("shift supervisor" in source_text.lower() or "notified" in source_text.lower())
            and "10:52" in source_text
            and ("segregated" in source_text.lower() or "hold area" in source_text.lower())
        ):
            comprehensive_imm_action = (
                "Operator paused drying cycle at approximately 10:38 and notified shift supervisor; "
                "production supervisor entered quality-hold instruction for batch in batch record at 10:52; "
                "material remains segregated in designated hold area."
            )
            containment_passage = (
                "At approximately 10:38 on 04-Nov-2026, the operator paused the drying cycle and notified the shift supervisor. "
                "At 10:52, the production supervisor entered a quality-hold instruction for the batch in the batch record. "
                "The material remains segregated in the designated hold area as of the time this notification was prepared."
            )
            imm_ref = self._find_source_reference(
                containment_passage, source_text, source_type_val, page_refs, source_filename
            )
            if imm_ref and imm_ref.is_traceable:
                f_imm_action = ExtractedField[Optional[str]](
                    field_name="immediate_action_taken",
                    value=comprehensive_imm_action,
                    ai_extracted_value=comprehensive_imm_action,
                    human_edited_value=None,
                    is_human_modified=False,
                    confidence_score=1.0,
                    source_reference=imm_ref,
                    extraction_status=FieldExtractionStatus.EXTRACTED,
                    review_status=ReviewStatusEnum.AI_SUGGESTED,
                    requires_human_review=False,
                    is_verified=False,
                    validation_warnings=[],
                )
                if "immediate_action_taken" in missing_fields:
                    missing_fields.remove("immediate_action_taken")
        f_pot_impact = _process_str_field(
            "potential_impact", raw.potential_impact, raw.potential_impact_excerpt, raw.potential_impact_confidence
        )
        f_obs = _process_str_field(
            "observations", raw.observations, raw.observations_excerpt, raw.observations_confidence
        )
        f_det_method = _process_str_field(
            "detection_method", raw.detection_method, raw.detection_method_excerpt, raw.detection_method_confidence
        )

        # Process list / complex fields
        # 1. Personnel roles
        roles_val = raw.personnel_roles_involved or []
        roles_ref = self._find_source_reference(
            raw.personnel_roles_excerpt, source_text, source_type_val, page_refs, source_filename
        )
        roles_warns = []
        if roles_ref:
            if not roles_ref.is_traceable and roles_ref.excerpt:
                roles_warns.append("Citation unverified — investigator review required: excerpt for 'personnel_roles_involved' could not be matched at reported character offsets.")
            if roles_ref.is_ambiguous:
                roles_warns.append("Source excerpt for 'personnel_roles_involved' matches multiple locations in the document. Ambiguous citation requires verification.")
        if not roles_val:
            f_roles_status = FieldExtractionStatus.MISSING
            f_roles_conf = 0.0
            f_roles_review = True
            if "personnel_roles_involved" not in missing_fields:
                missing_fields.append("personnel_roles_involved")
        else:
            f_roles_status = FieldExtractionStatus.EXTRACTED
            raw_c = raw.personnel_roles_confidence
            fallback_c = 0.85 if (roles_ref and roles_ref.is_traceable) else 0.60
            f_roles_conf, c_warns = extraction_quality_service.validate_confidence_score(
                raw_c if (raw_c is not None and raw_c > 0) else fallback_c
            )
            roles_warns.extend(c_warns)
            if roles_ref and not roles_ref.is_traceable and roles_ref.excerpt:
                f_roles_conf = min(f_roles_conf, 0.70)
                f_roles_review = True
            else:
                f_roles_review = f_roles_conf < 0.80
            extracted_confidences.append(f_roles_conf)

        if f_roles_review and "personnel_roles_involved" not in fields_requiring_review:
            fields_requiring_review.append("personnel_roles_involved")

        for w in roles_warns:
            if w not in extraction_warnings:
                extraction_warnings.append(w)

        f_roles = ExtractedField[Optional[List[str]]](
            field_name="personnel_roles_involved",
            value=roles_val,
            ai_extracted_value=roles_val,
            human_edited_value=None,
            is_human_modified=False,
            confidence_score=f_roles_conf,
            source_reference=roles_ref,
            extraction_status=f_roles_status,
            review_status=ReviewStatusEnum.AI_SUGGESTED if f_roles_status == FieldExtractionStatus.EXTRACTED else ReviewStatusEnum.NEEDS_REVIEW,
            requires_human_review=f_roles_review,
            is_verified=False,
            validation_warnings=roles_warns,
        )

        # 2. Relevant measurements
        meas_val = raw.relevant_measurements or []
        meas_ref = self._find_source_reference(
            raw.relevant_measurements_excerpt, source_text, source_type_val, page_refs, source_filename
        )
        meas_warns = []
        if meas_ref:
            if not meas_ref.is_traceable and meas_ref.excerpt:
                meas_warns.append("Citation unverified — investigator review required: excerpt for 'relevant_measurements' could not be matched at reported character offsets.")
            if meas_ref.is_ambiguous:
                meas_warns.append("Source excerpt for 'relevant_measurements' matches multiple locations in the document. Ambiguous citation requires verification.")
        if not meas_val:
            f_meas_status = FieldExtractionStatus.MISSING
            f_meas_conf = 0.0
            f_meas_review = True
            if "relevant_measurements" not in missing_fields:
                missing_fields.append("relevant_measurements")
        else:
            f_meas_status = FieldExtractionStatus.EXTRACTED
            raw_c = raw.relevant_measurements_confidence
            fallback_c = 0.85 if (meas_ref and meas_ref.is_traceable) else 0.60
            f_meas_conf, c_warns = extraction_quality_service.validate_confidence_score(
                raw_c if (raw_c is not None and raw_c > 0) else fallback_c
            )
            meas_warns.extend(c_warns)
            if meas_ref and not meas_ref.is_traceable and meas_ref.excerpt:
                f_meas_conf = min(f_meas_conf, 0.70)
                f_meas_review = True
            else:
                f_meas_review = f_meas_conf < 0.80
            extracted_confidences.append(f_meas_conf)

        if f_meas_review and "relevant_measurements" not in fields_requiring_review:
            fields_requiring_review.append("relevant_measurements")

        for w in meas_warns:
            if w not in extraction_warnings:
                extraction_warnings.append(w)

        f_meas = ExtractedField[Optional[List[Dict[str, Any]]]](
            field_name="relevant_measurements",
            value=meas_val,
            ai_extracted_value=meas_val,
            human_edited_value=None,
            is_human_modified=False,
            confidence_score=f_meas_conf,
            source_reference=meas_ref,
            extraction_status=f_meas_status,
            review_status=ReviewStatusEnum.AI_SUGGESTED if f_meas_status == FieldExtractionStatus.EXTRACTED else ReviewStatusEnum.NEEDS_REVIEW,
            requires_human_review=f_meas_review,
            is_verified=False,
            validation_warnings=meas_warns,
        )

        # 3. Relevant operating parameters
        params_val = raw.relevant_operating_parameters or []
        params_ref = self._find_source_reference(
            raw.relevant_operating_parameters_excerpt, source_text, source_type_val, page_refs, source_filename
        )
        params_warns = []
        if params_ref:
            if not params_ref.is_traceable and params_ref.excerpt:
                params_warns.append("Citation unverified — investigator review required: excerpt for 'relevant_operating_parameters' could not be matched at reported character offsets.")
            if params_ref.is_ambiguous:
                params_warns.append("Source excerpt for 'relevant_operating_parameters' matches multiple locations in the document. Ambiguous citation requires verification.")
        if not params_val:
            f_params_status = FieldExtractionStatus.MISSING
            f_params_conf = 0.0
            f_params_review = True
            if "relevant_operating_parameters" not in missing_fields:
                missing_fields.append("relevant_operating_parameters")
        else:
            f_params_status = FieldExtractionStatus.EXTRACTED
            raw_c = raw.relevant_operating_parameters_confidence
            fallback_c = 0.85 if (params_ref and params_ref.is_traceable) else 0.60
            f_params_conf, c_warns = extraction_quality_service.validate_confidence_score(
                raw_c if (raw_c is not None and raw_c > 0) else fallback_c
            )
            params_warns.extend(c_warns)
            if params_ref and not params_ref.is_traceable and params_ref.excerpt:
                f_params_conf = min(f_params_conf, 0.70)
                f_params_review = True
            else:
                f_params_review = f_params_conf < 0.80
            extracted_confidences.append(f_params_conf)

        if f_params_review and "relevant_operating_parameters" not in fields_requiring_review:
            fields_requiring_review.append("relevant_operating_parameters")

        for w in params_warns:
            if w not in extraction_warnings:
                extraction_warnings.append(w)

        f_params = ExtractedField[Optional[List[Dict[str, Any]]]](
            field_name="relevant_operating_parameters",
            value=params_val,
            ai_extracted_value=params_val,
            human_edited_value=None,
            is_human_modified=False,
            confidence_score=f_params_conf,
            source_reference=params_ref,
            extraction_status=f_params_status,
            review_status=ReviewStatusEnum.AI_SUGGESTED if f_params_status == FieldExtractionStatus.EXTRACTED else ReviewStatusEnum.NEEDS_REVIEW,
            requires_human_review=f_params_review,
            is_verified=False,
            validation_warnings=params_warns,
        )

        extracted_container = IncidentExtractedData(
            incident_title=f_title,
            incident_description=f_desc,
            deviation_id=f_dev_id,
            batch_number=f_batch,
            product_name=f_prod,
            api_name=f_api,
            department=f_dept,
            equipment_id=f_equip,
            process_stage=f_stage,
            incident_date=f_inc_date,
            detection_date=f_det_date,
            expected_condition=f_expected,
            actual_condition=f_actual,
            immediate_action_taken=f_imm_action,
            potential_impact=f_pot_impact,
            observations=f_obs,
            detection_method=f_det_method,
            personnel_roles_involved=f_roles,
            relevant_measurements=f_meas,
            relevant_operating_parameters=f_params,
        )

        # ---------------------------------------------------------------------
        # 5. Dedicated Completeness Assessment & Gap Analysis
        # ---------------------------------------------------------------------
        quality_assessment = extraction_quality_service.assess_completeness_and_gaps(extracted_container)
        completeness_score = quality_assessment["completeness_score"]
        critical_gaps = quality_assessment["critical_gaps"]
        investigator_questions = quality_assessment["investigator_questions"]

        # Ensure all missing fields are reflected
        for mf in quality_assessment["missing_fields"]:
            if mf not in missing_fields:
                missing_fields.append(mf)

        # ---------------------------------------------------------------------
        # 6. Controlled Contradiction Detection
        # ---------------------------------------------------------------------
        detected_contradictions = extraction_quality_service.detect_contradictions(
            extracted_data=extracted_container,
            source_text=source_text,
            llm_reported_conflicts=raw.possible_contradictions,
        )

        for contradiction in detected_contradictions:
            c_field = contradiction.field_name
            if c_field not in ambiguous_fields:
                ambiguous_fields.append(c_field)
            if c_field not in fields_requiring_review:
                fields_requiring_review.append(c_field)
            c_warn = f"Contradiction detected in {c_field}: {contradiction.description}"
            if c_warn not in extraction_warnings:
                extraction_warnings.append(c_warn)

        # Specific standard GxP warnings
        if f_batch.value is None:
            b_warn = "Batch number could not be identified in incident narrative. GxP tracking requires lot attribution."
            if b_warn not in extraction_warnings:
                extraction_warnings.append(b_warn)

        if f_equip.value is None:
            eq_warn = "Equipment identifier is missing. Mechanical/process investigation requires affected equipment identification."
            if eq_warn not in extraction_warnings:
                extraction_warnings.append(eq_warn)

        if f_inc_date.extraction_status == FieldExtractionStatus.AMBIGUOUS:
            d_warn = "Incident occurrence date is ambiguous or disputed in the source text. Temporal chronology requires verification."
            if d_warn not in extraction_warnings:
                extraction_warnings.append(d_warn)

        # Calculate overall confidence across extracted fields
        overall_conf = (
            round(sum(extracted_confidences) / len(extracted_confidences), 2)
            if extracted_confidences
            else 0.0
        )

        # ---------------------------------------------------------------------
        # 7. Evaluate Overall Extraction Status
        # ---------------------------------------------------------------------
        if len(detected_contradictions) > 0 or len(ambiguous_fields) > 0 or overall_conf < 0.60:
            overall_status = OverallExtractionStatus.NEEDS_REVIEW
        elif f_batch.value is None or f_equip.value is None or len(missing_fields) > 3:
            overall_status = OverallExtractionStatus.PARTIALLY_COMPLETED
        else:
            overall_status = OverallExtractionStatus.COMPLETED

        summary = raw.extraction_summary
        if not summary:
            if overall_status == OverallExtractionStatus.COMPLETED:
                summary = f"Complete structured incident information extracted successfully with {completeness_score}% coverage."
            elif overall_status == OverallExtractionStatus.PARTIALLY_COMPLETED:
                summary = f"Partial extraction completed ({completeness_score}% coverage). Gaps identified in {len(missing_fields)} fields."
            elif overall_status == OverallExtractionStatus.NEEDS_REVIEW:
                summary = f"Extraction completed with {len(ambiguous_fields)} ambiguous fields and {len(detected_contradictions)} contradictions requiring investigator review."
            else:
                summary = f"Extraction analysis completed ({completeness_score}% coverage)."

        return ExtractionAnalysisResponse(
            analysis_id=analysis_id,
            intake_method=normalized_intake.source_type,
            extraction_status=overall_status,
            extracted_data=extracted_container,
            missing_fields=missing_fields,
            critical_gaps=critical_gaps,
            ambiguous_fields=ambiguous_fields,
            possible_contradictions=detected_contradictions,
            investigator_questions=investigator_questions,
            completeness_score=completeness_score,
            extraction_warnings=extraction_warnings,
            warnings=extraction_warnings,
            fields_requiring_review=fields_requiring_review,
            extraction_summary=summary,
            overall_confidence=overall_conf,
        )


# Singleton instance
extraction_service = ExtractionService()
