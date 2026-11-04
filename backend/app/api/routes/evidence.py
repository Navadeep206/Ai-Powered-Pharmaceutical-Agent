"""Evidence and gap analysis route definitions for RootIQ."""

from typing import List
from fastapi import APIRouter, HTTPException, status
from app.schemas.evidence import EvidenceCreate, EvidenceResponse

router = APIRouter(prefix="/investigations/{investigation_id}/evidence", tags=["Evidence"])


@router.post(
    "",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach an evidence finding to an investigation",
    description="Validates and attaches supporting, contradictory, or missing evidence items.",
)
async def create_evidence(investigation_id: str, payload: EvidenceCreate):
    """Scaffolding contract: Validates evidence schema.

    Returns HTTP 501 Not Implemented pending database persistence.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Evidence persistence for investigation '{investigation_id}' will be implemented in Step 03 Phase 3.",
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
        detail=f"Evidence retrieval for investigation '{investigation_id}' will be implemented in Step 03 Phase 3.",
    )

