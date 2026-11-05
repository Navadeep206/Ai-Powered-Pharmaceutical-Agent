"""Corrective and Preventive Actions (CAPA) route definitions for RootIQ."""

from typing import List
from fastapi import APIRouter, HTTPException, status
from app.core.exceptions import CAPAError
from app.schemas.capa import CAPACreate, CAPAResponse
from app.services.capa_service import capa_service

router = APIRouter(prefix="/investigations/{investigation_id}/capa", tags=["CAPA"])


@router.post(
    "",
    response_model=CAPAResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new CAPA action for an investigation",
    description="Validates and associates a corrective or preventive remediation plan with an investigation adhering to FDA/ICH approval gates.",
)
async def create_capa(investigation_id: str, payload: CAPACreate):
    """Executes business validation on CAPA action proposals and prevents premature approval states.

    Returns HTTP 501 Not Implemented pending database persistence.
    """
    try:
        validated_capa = capa_service.validate_capa_creation(payload)
    except CAPAError as err:
        raise err

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"CAPA persistence for investigation '{investigation_id}' will be implemented in future phase; action validation succeeded.",
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
        detail=f"CAPA retrieval for investigation '{investigation_id}' will be implemented in future phase.",
    )
