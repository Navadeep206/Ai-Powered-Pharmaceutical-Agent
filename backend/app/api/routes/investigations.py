"""Investigation API route definitions for RootIQ."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.document import DocumentMetadataResponse
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationListResponse,
    InvestigationResponse,
    InvestigationStatusEnum,
    InvestigationUpdate,
    SeverityEnum,
)
from app.services.document_service import document_service
from app.services.investigation_service import investigation_service

router = APIRouter(prefix="/investigations", tags=["Investigations"])


@router.post(
    "",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new quality investigation",
    description="Validates incident particulars against pharmaceutical domain rules and persists a new investigation record in PostgreSQL.",
)
async def create_investigation(
    payload: InvestigationCreate,
    db: Session = Depends(get_db),
):
    """Executes validation, persists investigation record in PostgreSQL, and logs creation event."""
    return investigation_service.create_investigation(db=db, payload=payload)


@router.get(
    "",
    response_model=InvestigationListResponse,
    summary="List quality investigations",
    description="Retrieves a paginated collection of quality deviations with optional search, severity, status, and department filters.",
)
async def list_investigations(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(default=None, description="Free-text search query across title, description, batch, or number"),
    severity: Optional[SeverityEnum] = Query(default=None, description="Filter by risk severity"),
    status_filter: Optional[InvestigationStatusEnum] = Query(
        default=None, alias="status", description="Filter by investigation status"
    ),
    department: Optional[str] = Query(default=None, description="Filter by operational department"),
    db: Session = Depends(get_db),
):
    """Queries PostgreSQL for paginated investigations adhering to applied search and filter criteria."""
    return investigation_service.list_investigations(
        db=db,
        page=page,
        limit=limit,
        search=search,
        status_filter=status_filter,
        severity=severity,
        department=department,
    )


@router.get(
    "/{investigation_id}",
    response_model=InvestigationResponse,
    summary="Retrieve an investigation by ID or tracking number",
    description="Fetches comprehensive details of a specific deviation investigation by primary UUID or tracking number (INV-YYYY-XXXX).",
)
async def get_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
):
    """Queries PostgreSQL for a specific investigation by UUID or tracking number."""
    return investigation_service.get_investigation(db=db, identifier=investigation_id)


@router.patch(
    "/{investigation_id}",
    response_model=InvestigationResponse,
    summary="Update an existing investigation",
    description="Applies partial updates to an active investigation record following GxP lifecycle transition rules.",
)
async def update_investigation(
    investigation_id: str,
    payload: InvestigationUpdate,
    db: Session = Depends(get_db),
):
    """Executes business validation on update fields, transitions status, and persists changes in PostgreSQL."""
    return investigation_service.update_investigation(
        db=db,
        identifier=investigation_id,
        payload=payload,
    )


@router.get(
    "/{investigation_id}/documents",
    response_model=List[DocumentMetadataResponse],
    summary="List document metadata for an investigation",
    description="Retrieves persistent document intake metadata and extraction state linked to this deviation investigation from PostgreSQL.",
)
async def list_investigation_documents(
    investigation_id: str,
    db: Session = Depends(get_db),
):
    """Queries PostgreSQL for document records associated with this investigation."""
    docs = document_service.list_investigation_documents(db=db, investigation_id=investigation_id)
    return [
        DocumentMetadataResponse(
            document_id=str(d.id),
            investigation_id=str(d.investigation_id) if d.investigation_id else None,
            original_filename=d.original_filename,
            content_type=d.content_type,
            file_size_bytes=d.file_size,
            number_of_pages=d.page_count,
            source_type=d.source_type,
            extraction_status=d.extraction_status,
            created_at=d.created_at,
        )
        for d in docs
    ]
