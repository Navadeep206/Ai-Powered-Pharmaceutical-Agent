"""Corrective and Preventive Actions (CAPA) route definitions for RootIQ."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.capa import CAPACreate, CAPAResponse, CAPAStatusUpdate
from app.services.capa_service import capa_service

router = APIRouter(prefix="/investigations/{investigation_id}/capa", tags=["CAPA"])


@router.post(
    "",
    response_model=CAPAResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new CAPA action for an investigation",
    description="Validates and persists a corrective or preventive remediation plan with an investigation in PostgreSQL adhering to FDA/ICH approval gates.",
)
async def create_capa(
    investigation_id: str,
    payload: CAPACreate,
    db: Session = Depends(get_db),
):
    """Executes validation, persists CAPA action proposal in PostgreSQL, and logs activity."""
    return capa_service.create_capa(
        db=db,
        investigation_id=investigation_id,
        payload=payload,
    )


@router.get(
    "",
    response_model=List[CAPAResponse],
    summary="List all CAPA actions for an investigation",
    description="Retrieves corrective and preventive actions linked to this quality investigation from PostgreSQL.",
)
async def list_capa(
    investigation_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves all CAPA actions linked to this quality investigation."""
    return capa_service.list_capa(
        db=db,
        investigation_id=investigation_id,
    )


@router.patch(
    "/{capa_id}",
    response_model=CAPAResponse,
    summary="Update CAPA action status",
    description="Transitions CAPA action lifecycle state (Proposed -> Pending Review -> Approved -> In Progress -> Completed -> Closed) adhering to strict ICH Q10 gates.",
)
async def update_capa_status(
    investigation_id: str,
    capa_id: str,
    payload: CAPAStatusUpdate,
    db: Session = Depends(get_db),
):
    """Validates status transition and updates CAPA action record in PostgreSQL."""
    return capa_service.update_capa_status(
        db=db,
        investigation_id=investigation_id,
        capa_id=capa_id,
        payload=payload,
    )
