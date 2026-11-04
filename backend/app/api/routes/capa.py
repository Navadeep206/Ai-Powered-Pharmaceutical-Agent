"""Corrective and Preventive Actions (CAPA) route definitions for RootIQ."""

from typing import List
from fastapi import APIRouter, HTTPException, status
from app.schemas.capa import CAPACreate, CAPAResponse

router = APIRouter(prefix="/investigations/{investigation_id}/capa", tags=["CAPA"])


@router.post(
    "",
    response_model=CAPAResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new CAPA action for an investigation",
    description="Validates and associates a corrective or preventive remediation plan with an investigation.",
)
async def create_capa(investigation_id: str, payload: CAPACreate):
    """Scaffolding contract: Validates CAPA proposal schema.

    Returns HTTP 501 Not Implemented pending database persistence.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"CAPA persistence for investigation '{investigation_id}' will be implemented in Step 03 Phase 3.",
    )


@router.get(
    "",
    response_model=List[CAPAResponse],
    summary="List all CAPA actions for an investigation",
    description="Retrieves corrective and preventive actions linked to this quality investigation.",
)
async def list_capa(investigation_id: str):
    """Scaffolding contract: Returns HTTP 501 Not Implemented pending database integration."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"CAPA retrieval for investigation '{investigation_id}' will be implemented in Step 03 Phase 3.",
    )
