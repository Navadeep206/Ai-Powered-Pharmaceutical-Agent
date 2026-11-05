"""Pharmaceutical Incident Extraction Quality & Validation Service for RootIQ.

Performs deterministic GxP validation, completeness scoring, critical gap analysis,
evidence-based contradiction detection, and investigator inquiry recommendation.
Ensures machine-extracted information is rigorously audited before human review.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.logging import get_logger
from app.schemas.extraction import (
    CriticalGapItem,
    ExtractedField,
    FieldExtractionStatus,
    IncidentExtractedData,
    PossibleContradiction,
    ReviewStatusEnum,
    SourceReference,
)

logger = get_logger("services.extraction_quality")

# Weighted field registry for transparent document coverage calculation.
# Total weights sum to 100.0%.
FIELD_WEIGHTS: Dict[str, float] = {
    # Critical GxP Fields (40%)
    "batch_number": 15.0,
    "equipment_id": 10.0,
    "incident_date": 10.0,
    "incident_description": 5.0,
    # High-Priority Process Fields (35%)
    "actual_condition": 10.0,
    "expected_condition": 10.0,
    "process_stage": 8.0,
    "immediate_action_taken": 7.0,
    # Supporting Context Fields (25%)
    "api_name": 4.0,
    "product_name": 4.0,
    "department": 3.0,
    "deviation_id": 3.0,
    "detection_date": 2.0,
    "detection_method": 2.0,
    "potential_impact": 2.0,
    "relevant_measurements": 2.0,
    "relevant_operating_parameters": 1.0,
    "observations": 1.0,
    "personnel_roles_involved": 1.0,
}


class ExtractionQualityService:
    """Service providing quality assessment, contradiction analysis, and validation audits."""

    def __init__(self):
        pass

    # -------------------------------------------------------------------------
    # 1. FIELD-LEVEL VALIDATION
    # -------------------------------------------------------------------------

    def validate_date_format(self, date_str: Optional[str]) -> Tuple[Optional[str], List[str]]:
        """Validate whether date conforms strictly to ISO-8601 (YYYY-MM-DD).

        Does NOT guess, extrapolate, or silently alter invalid dates.
        """
        if not date_str:
            return None, []

        clean_date = date_str.strip()
        warnings = []

        # Check standard ISO YYYY-MM-DD pattern
        iso_pattern = r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$"
        if not re.match(iso_pattern, clean_date):
            warnings.append(
                f"Date value '{clean_date}' does not conform to ISO-8601 YYYY-MM-DD format. "
                "Human investigator verification is required."
            )
            return clean_date, warnings

        # Semantic date validation (valid calendar day)
        try:
            datetime.strptime(clean_date, "%Y-%m-%d")
        except ValueError:
            warnings.append(
                f"Date value '{clean_date}' is not a valid calendar date. "
                "Human investigator verification is required."
            )

        return clean_date, warnings

    def validate_confidence_score(self, confidence: Optional[float]) -> Tuple[float, List[str]]:
        """Validate confidence score falls strictly within [0.0, 1.0].

        Clamps out-of-range values and records explicit validation warnings.
        """
        warnings = []
        if confidence is None:
            return 0.0, warnings

        try:
            conf_val = float(confidence)
        except (ValueError, TypeError):
            warnings.append(f"Invalid non-numeric confidence value '{confidence}'. Defaulting to 0.0.")
            return 0.0, warnings

        if conf_val < 0.0:
            warnings.append(f"Negative confidence score {conf_val} detected. Clamped to 0.0.")
            return 0.0, warnings
        elif conf_val > 1.0:
            warnings.append(f"Confidence score {conf_val} exceeds 1.0. Clamped to 1.0.")
            return 1.0, warnings

        return round(conf_val, 2), warnings

    def validate_source_traceability(
        self,
        source_ref: Optional[SourceReference],
        source_text: str,
    ) -> Tuple[Optional[SourceReference], List[str]]:
        """Validate character offsets against normalized source text.

        Ensures referenced excerpt actually exists at the reported offsets.
        If offsets are mismatched, clears offsets and marks is_traceable=False.
        """
        if not source_ref or not source_ref.excerpt:
            return source_ref, []

        warnings = []
        excerpt = source_ref.excerpt.strip()
        start = source_ref.char_offset_start
        end = source_ref.char_offset_end

        if start is not None and end is not None:
            # Check bounds
            if start < 0 or end > len(source_text) or start >= end:
                warnings.append(
                    f"Character offsets [{start}:{end}] are out of bounds for source text of length {len(source_text)}."
                )
                source_ref.char_offset_start = None
                source_ref.char_offset_end = None
                source_ref.is_traceable = False
                return source_ref, warnings

            # Check exact substring match
            actual_slice = source_text[start:end]
            if actual_slice != excerpt:
                # Check case-insensitive
                if actual_slice.lower() == excerpt.lower():
                    # Tolerable casing difference
                    pass
                else:
                    warnings.append(
                        f"Reported offsets [{start}:{end}] yield '{actual_slice[:30]}...', "
                        f"which does not match cited excerpt '{excerpt[:30]}...'."
                    )
                    source_ref.char_offset_start = None
                    source_ref.char_offset_end = None
                    source_ref.is_traceable = False
        else:
            # Excerpt provided without verified offsets
            source_ref.is_traceable = False

        return source_ref, warnings

    # -------------------------------------------------------------------------
    # 2. COMPLETENESS & QUALITY ASSESSMENT
    # -------------------------------------------------------------------------

    def assess_completeness_and_gaps(
        self,
        extracted_data: IncidentExtractedData,
    ) -> Dict[str, Any]:
        """Compute transparent document information coverage and identify critical GxP evidence gaps.

        The completeness score represents source document information coverage,
        NOT the probability that the incident extraction is factual.
        """
        missing_fields: List[str] = []
        critical_gaps: List[str] = []
        structured_gaps: List[CriticalGapItem] = []
        investigator_questions: List[str] = []
        awarded_weight = 0.0

        for field_name, weight in FIELD_WEIGHTS.items():
            field_obj: ExtractedField = getattr(extracted_data, field_name, None)
            is_populated = False

            if field_obj is not None:
                val = field_obj.value
                if val is not None:
                    if isinstance(val, (list, dict)):
                        is_populated = len(val) > 0
                    elif isinstance(val, str):
                        clean = val.strip()
                        is_populated = len(clean) > 0 and clean.lower() not in (
                            "null",
                            "none",
                            "n/a",
                            "unknown",
                            "not specified",
                            "not mentioned",
                        )
                    else:
                        is_populated = True

            if is_populated and field_obj.extraction_status != FieldExtractionStatus.MISSING:
                awarded_weight += weight
            else:
                missing_fields.append(field_name)

        # Evaluate Critical GxP Gaps & Investigator Questions
        # A. Batch Number
        if "batch_number" in missing_fields:
            gap = CriticalGapItem(
                field_name="batch_number",
                category="Critical GxP",
                rationale="Batch/Lot identifier is missing. Lot traceability is mandatory under 21 CFR 211.188 for pharmaceutical deviation tracking.",
                suggested_action="Review Master Batch Record (MBR) or dispensing log to confirm the exact batch number.",
            )
            critical_gaps.append(f"Critical GxP Gap: {gap.rationale}")
            structured_gaps.append(gap)
            investigator_questions.append(
                "What was the specific API lot or batch identifier undergoing processing during the deviation?"
            )

        # B. Equipment ID
        if "equipment_id" in missing_fields:
            gap = CriticalGapItem(
                field_name="equipment_id",
                category="Critical GxP",
                rationale="Equipment identifier is missing. Investigation cannot correlate preventative maintenance, calibration, or cleaning validation records.",
                suggested_action="Identify specific reactor vessel, filtration unit, or analytical instrument tag from DCS/SCADA logs.",
            )
            critical_gaps.append(f"Critical GxP Gap: {gap.rationale}")
            structured_gaps.append(gap)
            investigator_questions.append(
                "Which specific reactor vessel, filtration unit, or machinery tag was involved in the excursion?"
            )

        # C. Incident Date
        if "incident_date" in missing_fields:
            gap = CriticalGapItem(
                field_name="incident_date",
                category="Critical GxP",
                rationale="Incident occurrence date is missing. Regulatory reporting timelines (e.g. 24h/72h notification window) cannot be audited.",
                suggested_action="Confirm deviation start timestamp from historian SCADA event logs.",
            )
            critical_gaps.append(f"Critical GxP Gap: {gap.rationale}")
            structured_gaps.append(gap)
            investigator_questions.append(
                "What was the exact verified calendar date and UTC timestamp when the excursion commenced?"
            )

        # D. Actual Condition
        if "actual_condition" in missing_fields:
            gap = CriticalGapItem(
                field_name="actual_condition",
                category="High-Priority",
                rationale="Observed abnormal condition is unquantified, preventing engineering evaluation of excursion severity.",
                suggested_action="Obtain calibrated analytical assay, sensor log, or peak temperature reading during deviation window.",
            )
            critical_gaps.append(f"High-Priority Gap: {gap.rationale}")
            structured_gaps.append(gap)
            investigator_questions.append(
                "What was the peak measured value or abnormal reading recorded on calibrated instrumentation?"
            )

        # E. Expected Condition
        if "expected_condition" in missing_fields:
            gap = CriticalGapItem(
                field_name="expected_condition",
                category="High-Priority",
                rationale="Validated normal operating parameter range or specification limit is not referenced.",
                suggested_action="Confirm validated parameter operating ranges in approved Standard Operating Procedure (SOP).",
            )
            structured_gaps.append(gap)
            investigator_questions.append(
                "What is the validated operating limit or parameter target range specified in the Master Batch Record?"
            )

        # F. Immediate Action Taken
        if "immediate_action_taken" in missing_fields:
            gap = CriticalGapItem(
                field_name="immediate_action_taken",
                category="High-Priority",
                rationale="Immediate containment actions are not documented, creating potential ongoing batch contamination risk.",
                suggested_action="Document operator containment response, lot quarantine, or equipment shutdown steps.",
            )
            critical_gaps.append(f"High-Priority Gap: {gap.rationale}")
            structured_gaps.append(gap)
            investigator_questions.append(
                "What immediate containment, quarantine, or mitigation actions were executed by operating personnel?"
            )

        # G. Potential Impact
        if "potential_impact" in missing_fields:
            investigator_questions.append(
                "Has Quality Assurance evaluated potential impact on API polymorphic form, impurity profile, or stability?"
            )

        # H. Operating Parameters or Measurements
        if "relevant_measurements" in missing_fields:
            investigator_questions.append(
                "Are DCS/SCADA temperature traces, pressure logs, or IPC assay data sheets available for attachment?"
            )

        completeness_score = round(awarded_weight, 1)

        return {
            "completeness_score": completeness_score,
            "missing_fields": missing_fields,
            "critical_gaps": critical_gaps,
            "structured_gaps": structured_gaps,
            "investigator_questions": investigator_questions,
        }

    # -------------------------------------------------------------------------
    # 3. CONTROLLED CONTRADICTION DETECTION
    # -------------------------------------------------------------------------

    def detect_contradictions(
        self,
        extracted_data: IncidentExtractedData,
        source_text: str,
        llm_reported_conflicts: Optional[List[Dict[str, Any]]] = None,
    ) -> List[PossibleContradiction]:
        """Detect and preserve conflicting statements, identifiers, or measurements.

        Preserves both candidate values without silently picking one.
        Labels conflicts as INVESTIGATOR_REVIEW_REQUIRED.
        """
        contradictions: List[PossibleContradiction] = []
        discovered_conflict_fields: Set[str] = set()

        # 1. Incorporate LLM-identified conflicts if provided
        if llm_reported_conflicts:
            for item in llm_reported_conflicts:
                field_name = item.get("field_name")
                conflicting_vals = item.get("conflicting_values", [])
                desc = item.get("description", "Discrepancy noted in source statements.")
                if field_name and len(conflicting_vals) >= 2:
                    contradictions.append(
                        PossibleContradiction(
                            field_name=field_name,
                            conflicting_values=[str(v) for v in conflicting_vals],
                            source_references=[],
                            description=desc,
                            resolution_status="INVESTIGATOR_REVIEW_REQUIRED",
                        )
                    )
                    discovered_conflict_fields.add(field_name)

        # 2. Heuristic contradiction detection: Conflicting Batch Numbers
        if "batch_number" not in discovered_conflict_fields:
            # Match standard API lot/batch identifiers
            batch_candidates = set()
            for m in re.findall(r"\b(?:BATCH|LOT)[-_][A-Z0-9]+(?:-[A-Z0-9]+)*\b", source_text, re.IGNORECASE):
                batch_candidates.add(m.upper())
            for m in re.findall(r"\b(?:BATCH|LOT)[#:\s]+([0-9]{4,10})\b", source_text, re.IGNORECASE):
                batch_candidates.add(f"BATCH-{m.upper()}")

            if len(batch_candidates) >= 2:
                refs = []
                for b_raw in batch_candidates:
                    start = source_text.find(b_raw)
                    if start == -1:
                        # Try case-insensitive find
                        start = source_text.upper().find(b_raw)
                    if start != -1:
                        refs.append(
                            SourceReference(
                                excerpt=b_raw,
                                char_offset_start=start,
                                char_offset_end=start + len(b_raw),
                            )
                        )
                contradictions.append(
                    PossibleContradiction(
                        field_name="batch_number",
                        conflicting_values=sorted(list(batch_candidates)),
                        source_references=refs,
                        description=(
                            f"Multiple distinct batch identifiers discovered in source narrative ({', '.join(sorted(batch_candidates))}). "
                            "GxP traceability requires verified lot attribution."
                        ),
                        resolution_status="INVESTIGATOR_REVIEW_REQUIRED",
                    )
                )
                discovered_conflict_fields.add("batch_number")

        # 3. Heuristic contradiction detection: Conflicting Incident Dates
        if "incident_date" not in discovered_conflict_fields:
            date_matches = set(re.findall(r"\b(20\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))\b", source_text))
            if len(date_matches) >= 2:
                # Check if multiple dates are associated with occurrence
                refs = []
                for d in date_matches:
                    start = source_text.find(d)
                    if start != -1:
                        refs.append(
                            SourceReference(
                                excerpt=d,
                                char_offset_start=start,
                                char_offset_end=start + len(d),
                            )
                        )
                # Only flag as conflict if incident_date extraction was marked ambiguous or multiple dates exist
                if (
                    extracted_data.incident_date.extraction_status == FieldExtractionStatus.AMBIGUOUS
                    or len(date_matches) > 2
                ):
                    contradictions.append(
                        PossibleContradiction(
                            field_name="incident_date",
                            conflicting_values=sorted(list(date_matches)),
                            source_references=refs,
                            description=(
                                f"Multiple candidate occurrence dates identified ({', '.join(sorted(date_matches))}). "
                                "Investigation must establish exact chronology."
                            ),
                            resolution_status="INVESTIGATOR_REVIEW_REQUIRED",
                        )
                    )
                    discovered_conflict_fields.add("incident_date")

        # 4. Heuristic contradiction detection: Conflicting Equipment Tags
        if "equipment_id" not in discovered_conflict_fields:
            equip_matches = set(re.findall(r"\b([RCFV]-\d{3}[A-Z]?)\b", source_text))
            if len(equip_matches) >= 2:
                refs = []
                for eq in equip_matches:
                    start = source_text.find(eq)
                    if start != -1:
                        refs.append(
                            SourceReference(
                                excerpt=eq,
                                char_offset_start=start,
                                char_offset_end=start + len(eq),
                            )
                        )
                contradictions.append(
                    PossibleContradiction(
                        field_name="equipment_id",
                        conflicting_values=sorted(list(equip_matches)),
                        source_references=refs,
                        description=(
                            f"Multiple equipment identifiers referenced ({', '.join(sorted(equip_matches))}). "
                            "Discrepancy must be reviewed by lead investigator to isolate affected unit."
                        ),
                        resolution_status="INVESTIGATOR_REVIEW_REQUIRED",
                    )
                )
                discovered_conflict_fields.add("equipment_id")

        # 5. Heuristic contradiction detection: Conflicting Temperature Measurements
        if "relevant_measurements" not in discovered_conflict_fields:
            temp_matches = re.findall(r"(\d{2,3}(?:\.\d+)?)\s*(?:°C|deg C|degrees C)", source_text, re.IGNORECASE)
            distinct_temps = sorted(list(set(temp_matches)), key=lambda x: float(x))
            # If multiple distinct temperatures are reported above normal range (e.g. excursion temps)
            if len(distinct_temps) >= 2:
                # Check if there are contradictory high temperatures (e.g. 84.5 °C vs 92.0 °C)
                high_temps = [t for t in distinct_temps if float(t) > 75.0]
                if len(high_temps) >= 2:
                    refs = []
                    for t in high_temps:
                        t_snippet = f"{t} °C"
                        start = source_text.find(t)
                        if start != -1:
                            refs.append(
                                SourceReference(
                                    excerpt=t_snippet,
                                    char_offset_start=start,
                                    char_offset_end=start + len(t),
                                )
                            )
                    contradictions.append(
                        PossibleContradiction(
                            field_name="relevant_measurements",
                            conflicting_values=[f"{t} °C" for t in high_temps],
                            source_references=refs,
                            description=(
                                f"Discrepant peak temperatures reported during excursion ({', '.join(high_temps)} °C). "
                                "Sensor calibration and DCS alarm data required to resolve true peak value."
                            ),
                            resolution_status="INVESTIGATOR_REVIEW_REQUIRED",
                        )
                    )

        return contradictions


# Singleton instance
extraction_quality_service = ExtractionQualityService()
