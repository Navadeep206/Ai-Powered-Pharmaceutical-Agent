"""Evidence and gap analysis route definitions for RootIQ."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.evidence import EvidenceCreate, EvidenceResponse, EvidenceUpdate
from app.services.evidence_service import evidence_service

router = APIRouter(prefix="/investigations/{investigation_id}/evidence", tags=["Evidence"])


@router.post(
    "",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach an evidence finding to an investigation",
    description="Validates and persists supporting, contradictory, missing evidence, or investigator questions in PostgreSQL.",
)
async def create_evidence(
    investigation_id: str,
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
):
    """Executes business validation, persists evidence record, and logs event in activity history."""
    return evidence_service.create_evidence(
        db=db,
        investigation_id=investigation_id,
        payload=payload,
    )


@router.get(
    "",
    response_model=List[EvidenceResponse],
    summary="List all evidence items for an investigation",
    description="Retrieves evidence findings, contradictory data, and investigator queries linked to this deviation from PostgreSQL.",
)
async def list_evidence(
    investigation_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves all evidence records linked to this quality investigation."""
    return evidence_service.list_evidence(
        db=db,
        investigation_id=investigation_id,
    )


@router.patch(
    "/{evidence_id}",
    response_model=EvidenceResponse,
    summary="Update an evidence finding review status or notes",
    description="Updates verification review status (Pending Review -> Verified / Rejected) and persists changes to PostgreSQL.",
)
async def update_evidence(
    investigation_id: str,
    evidence_id: str,
    payload: EvidenceUpdate,
    db: Session = Depends(get_db),
):
    """Updates evidence review status and records audit log in activity history."""
    return evidence_service.update_evidence(
        db=db,
        investigation_id=investigation_id,
        evidence_id=evidence_id,
        payload=payload,
    )
