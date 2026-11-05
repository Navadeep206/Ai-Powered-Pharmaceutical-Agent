"""Root Cause Analysis (RCA) route definitions for RootIQ."""

from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.rca import RCAGenerateRequest, RCARequest, RCAResponse, RCAWorkflowResult
from app.services.rca_service import rca_service

router = APIRouter(prefix="/investigations/{investigation_id}/rca", tags=["Root Cause Analysis"])


@router.post(
    "",
    response_model=RCAResponse,
    status_code=status.HTTP_200_OK,
    summary="Save or update RCA findings for an investigation",
    description="Validates and persists 5-Whys causal chains and Ishikawa 6M fishbone models in PostgreSQL adhering to ICH Q9 principles.",
)
async def save_rca_analysis(
    investigation_id: str,
    payload: RCARequest,
    db: Session = Depends(get_db),
):
    """Executes validation, persists RCA analysis with child causal elements in a single transaction, and logs activity."""
    return rca_service.save_rca_analysis(
        db=db,
        investigation_id=investigation_id,
        payload=payload,
    )


@router.post(
    "/generate",
    response_model=RCAWorkflowResult,
    status_code=status.HTTP_200_OK,
    summary="Execute AI-assisted RCA reasoning workflow",
    description="Runs LangGraph RCA workflow: 5-Whys, Ishikawa 6M Fishbone, Evidence Analysis, and Root Cause Synthesis.",
)
async def generate_rca_analysis(
    investigation_id: str,
    payload: Optional[RCAGenerateRequest] = None,
    db: Session = Depends(get_db),
):
    """Orchestrates LangGraph RCA reasoning engine with Groq LLM and transactional PostgreSQL persistence."""
    return rca_service.generate_rca(
        db=db,
        investigation_id=investigation_id,
        payload=payload,
    )


@router.get(
    "",
    response_model=RCAResponse,
    summary="Retrieve RCA findings for an investigation",
    description="Fetches the active 5-Whys chain and Ishikawa 6M causes associated with this investigation from PostgreSQL.",
)
async def get_rca_analysis(
    investigation_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves the latest RCA analysis tree for an investigation from PostgreSQL."""
    return rca_service.get_rca_analysis(
        db=db,
        investigation_id=investigation_id,
    )

