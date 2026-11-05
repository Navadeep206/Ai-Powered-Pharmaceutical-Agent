"""Root Cause Analysis (RCA) Business Service for RootIQ.

Enforces strict causal chain integrity, 6M Ishikawa categorization,
and human-in-the-loop verification boundaries adhering to ICH Q9 principles.
"""

from datetime import datetime, timezone
from typing import List, Optional
from app.core.exceptions import (
    InvalidFishboneCategoryError,
    InvalidFiveWhysStructureError,
    InvalidRCACauseStatusError,
)
from app.core.logging import get_logger
from app.schemas.rca import (
    CauseVerificationStatusEnum,
    FishboneCategoryEnum,
    FishboneCause,
    FiveWhysLevel,
    RCARequest,
    RCAResponse,
)

logger = get_logger("services.rca")


class RCAService:
    """Service providing RCA validation and causal chain verification."""

    def validate_five_whys(self, five_whys: List[FiveWhysLevel]) -> List[FiveWhysLevel]:
        """Validate sequential ordering, non-empty questions/answers, and root cause designation."""
        if not five_whys:
            return []

        if len(five_whys) > 5:
            raise InvalidFiveWhysStructureError(
                f"5-Whys methodology supports at most 5 sequential levels (provided {len(five_whys)})."
            )

        root_cause_count = 0
        validated_levels: List[FiveWhysLevel] = []

        for idx, item in enumerate(five_whys):
            expected_level = idx + 1
            if item.level != expected_level:
                raise InvalidFiveWhysStructureError(
                    f"5-Whys levels must be strictly sequential without gaps. Expected level {expected_level}, received {item.level}."
                )

            if not item.question or not item.question.strip():
                raise InvalidFiveWhysStructureError(f"Why #{item.level} question cannot be empty.")
            if not item.answer or not item.answer.strip():
                raise InvalidFiveWhysStructureError(f"Why #{item.level} answer cannot be empty.")

            # Rule: AI suggestions cannot be automatically marked as Confirmed Root Cause
            if item.status == CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE and not item.is_root_cause:
                raise InvalidRCACauseStatusError(
                    f"Why #{item.level} has status 'Confirmed Root Cause' but is_root_cause is False."
                )

            if item.is_root_cause:
                root_cause_count += 1
                # Must be the final level in the presented chain
                if idx != len(five_whys) - 1:
                    raise InvalidFiveWhysStructureError(
                        f"Root cause was designated at level {item.level}, but subsequent Why levels ({[x.level for x in five_whys[idx+1:]]}) exist. The primary root cause must be the terminal step of the causal sequence."
                    )

            validated_levels.append(item)

        if root_cause_count > 1:
            raise InvalidFiveWhysStructureError("Only one primary root cause may be designated in a single 5-Whys tree.")

        return validated_levels

    def validate_fishbone_causes(self, causes: List[FishboneCause]) -> List[FishboneCause]:
        """Validate Ishikawa 6M causes, evidence citations, and human confirmation gates."""
        if not causes:
            return []

        validated_causes: List[FishboneCause] = []

        for cause in causes:
            if not cause.cause_id or not cause.cause_id.strip():
                raise InvalidRCACauseStatusError("Each fishbone cause must specify a unique cause_id.")

            if not cause.cause_description or not cause.cause_description.strip():
                raise InvalidRCACauseStatusError(
                    f"Cause '{cause.cause_id}' must provide a non-empty description."
                )

            # Check category validity
            if cause.category not in FishboneCategoryEnum:
                raise InvalidFishboneCategoryError(
                    f"Invalid Fishbone category '{cause.category}'. Must be one of: {[c.value for c in FishboneCategoryEnum]}."
                )

            # Strict GxP Rule: A root cause cannot be confirmed without supporting empirical evidence
            if cause.status == CauseVerificationStatusEnum.CONFIRMED_ROOT_CAUSE:
                if not cause.evidence_references or len(cause.evidence_references) == 0:
                    raise InvalidRCACauseStatusError(
                        f"Cause '{cause.cause_id}' cannot be marked as 'Confirmed Root Cause' without citing supporting evidence references."
                    )

            validated_causes.append(cause)

        return validated_causes

    def validate_rca_request(self, payload: RCARequest) -> RCARequest:
        """Execute full validation across 5-Whys and Fishbone structures."""
        validated_five_whys = self.validate_five_whys(payload.five_whys)
        validated_fishbone = self.validate_fishbone_causes(payload.fishbone_causes)

        return RCARequest(
            five_whys=validated_five_whys,
            fishbone_causes=validated_fishbone,
            investigator_notes=payload.investigator_notes.strip() if payload.investigator_notes else None,
        )

    def prepare_rca_response(
        self,
        investigation_id: str,
        validated_rca: RCARequest,
    ) -> RCAResponse:
        """Construct full RCAResponse contract."""
        return RCAResponse(
            investigation_id=investigation_id,
            five_whys=validated_rca.five_whys,
            fishbone_causes=validated_rca.fishbone_causes,
            investigator_notes=validated_rca.investigator_notes,
            updated_at=datetime.now(timezone.utc),
        )


# Singleton service instance
rca_service = RCAService()
