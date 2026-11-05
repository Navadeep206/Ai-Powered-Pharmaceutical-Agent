"""Corrective and Preventive Actions (CAPA) route definitions for RootIQ."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.agents.graph import resume_capa_workflow
from app.database.session import get_db
from app.schemas.capa import (
    CAPACreate,
    CAPAGenerateRequest,
    CAPAResponse,
    CAPAReviewRequest,
    CAPAStatusUpdate,
    CAPAWorkflowResult,
)
from app.services.capa_service import capa_service

router = APIRouter(prefix="/investigations/{investigation_id}/capa", tags=["CAPA"])
global_router = APIRouter(prefix="/capa", tags=["CAPA"])


@global_router.get(
    "",
    response_model=List[CAPAResponse],
    summary="List all CAPA actions across investigations",
    description="Retrieves enterprise portfolio of CAPA actions across investigations with optional status and search filtering.",
)
async def list_all_capas(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Retrieves all corrective and preventive actions from PostgreSQL."""
    return capa_service.list_all_capa(
        db=db,
        limit=limit,
        offset=offset,
        status=status,
        search=search,
    )


@router.post(
    "/generate",
    response_model=CAPAWorkflowResult,
    status_code=status.HTTP_200_OK,
    summary="Generate AI-assisted CAPA recommendations",
    description="Executes LangGraph CAPA generation and validation, pausing at human QA review boundary.",
)
async def generate_capa(
    investigation_id: str,
    payload: Optional[CAPAGenerateRequest] = None,
    db: Session = Depends(get_db),
):
    """Initiates AI CAPA generation workflow with Groq LLM and pauses at the human QA review boundary."""
    problem_statement = payload.problem_statement if payload else None
    persist = payload.persist if payload else True
    return capa_service.generate_capa(
        db=db,
        investigation_id=investigation_id,
        problem_statement=problem_statement,
        persist=persist,
    )


@router.post(
    "/review",
    response_model=CAPAWorkflowResult,
    status_code=status.HTTP_200_OK,
    summary="Submit human QA review decisions for CAPA recommendations",
    description="Applies human review decisions (Approval, Rejection, Modification) and resumes paused LangGraph thread if provided.",
)
async def review_capa(
    investigation_id: str,
    payload: CAPAReviewRequest,
    db: Session = Depends(get_db),
):
    """Records human review decisions and resumes workflow if thread_id is specified."""
    if payload.thread_id:
        return resume_capa_workflow(
            thread_id=payload.thread_id,
            review_request=payload,
            db=db,
        )

    # If no thread_id, apply decisions directly to existing records in PostgreSQL
    updated_actions = capa_service.apply_capa_review_decisions(
        db=db,
        investigation_id=investigation_id,
        decisions=payload.decisions,
        reviewer_comments=payload.general_comments,
    )

    all_actions = capa_service.list_capa(db, investigation_id)
    # Convert list to recommendations representation
    return CAPAWorkflowResult(
        workflow_id=f"WF-REV-{investigation_id[:8]}",
        investigation_id=investigation_id,
        thread_id=payload.thread_id or "direct-review",
        rca_summary=f"Human review applied for {len(payload.decisions)} CAPA recommendations.",
        capa_recommendations=[],
        approved_actions=[],
        rejected_actions=[],
        pending_actions=[],
        capa_generation_status="COMPLETED",
        capa_review_status="REVIEWED",
        human_review_required=False,
        workflow_completion_status="COMPLETED",
        persisted_in_db=True,
        persisted_capa_ids=[a.action_id for a in all_actions],
    )


@router.post(
    "/resume",
    response_model=CAPAWorkflowResult,
    status_code=status.HTTP_200_OK,
    summary="Resume paused CAPA workflow with review decisions",
    description="Resumes a checkpointed LangGraph thread waiting at the human review boundary.",
)
async def resume_capa(
    investigation_id: str,
    payload: CAPAReviewRequest,
    db: Session = Depends(get_db),
):
    """Resumes paused LangGraph thread using the provided thread_id and review decisions."""
    if not payload.thread_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'thread_id' is required to resume a paused CAPA workflow.",
        )
    return resume_capa_workflow(
        thread_id=payload.thread_id,
        review_request=payload,
        db=db,
    )


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

