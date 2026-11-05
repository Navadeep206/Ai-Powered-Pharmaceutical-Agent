"""Evidence and gap analysis route definitions for RootIQ."""

from typing import List
from fastapi import APIRouter, HTTPException, status
from app.core.exceptions import EvidenceError
from app.schemas.evidence import EvidenceCreate, EvidenceResponse
from app.services.evidence_service import evidence_service

router = APIRouter(prefix="/investigations/{investigation_id}/evidence", tags=["Evidence"])


@router.post(
    "",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach an evidence finding to an investigation",
    description="Validates and attaches supporting, contradictory, or missing evidence items.",
)
async def create_evidence(investigation_id: str, payload: EvidenceCreate):
    """Executes business validation on evidence description, type, and source citations.

    Returns HTTP 501 Not Implemented pending database persistence.
    """
    try:
        validated_evidence = evidence_service.validate_evidence(payload)
    except EvidenceError as err:
        raise err

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Evidence persistence for investigation '{investigation_id}' will be implemented in future phase; validation succeeded.",
    )


@router.get(
    "",
    response_model=List[EvidenceResponse],
    summary="List all evidence items for an investigation",
    description="Retrieves evidence findings, contradictory data, and investigator queries linked to this deviation.",
)
async def list_evidence(investigation_id: str):
    """Scaffolding contract: Returns HTTP 501 Not Implemented pending database integration."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Evidence retrieval for investigation '{investigation_id}' will be implemented in future phase.",
    )
