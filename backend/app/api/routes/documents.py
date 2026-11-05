"""Document upload and incident intake route definitions."""

from typing import Optional, Union
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session
from app.agents import run_incident_extraction_workflow
from app.core.exceptions import (
    AIAuthenticationError,
    AITimeoutError,
    DocumentProcessingError,
    IncidentIntakeError,
)
from app.database.session import get_db
from app.schemas.document import (
    DocumentAnalysisRequest,
    DocumentExtractionResult,
    NormalizedIncidentIntake,
)
from app.schemas.extraction import (
    ExtractionAnalysisResponse,
    OverallExtractionStatus,
)
from app.services.document_service import document_service
from app.services.extraction_service import extraction_service
from app.services.intake_service import intake_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentExtractionResult,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and extract text from an incident PDF",
    description="Validates multipart PDF file structure, extracts text page-by-page, and detects scanned pages requiring OCR. If investigation_id is provided, persists metadata in PostgreSQL.",
)
async def upload_document(
    file: UploadFile = File(...),
    investigation_id: Optional[str] = Query(
        default=None,
        description="Optional investigation ID to associate document metadata with in PostgreSQL",
    ),
    db: Session = Depends(get_db),
):
    """Validates PDF file, extracts text in-memory, and conditionally records metadata in PostgreSQL."""
    # Check basic file extension
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf") and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF documents (*.pdf) are accepted for incident intake.",
        )

    try:
        file_bytes = await file.read()
        extraction_result = document_service.extract_text_from_pdf_bytes(
            file_bytes=file_bytes,
            filename=filename,
        )

        # Conditionally persist metadata in PostgreSQL if investigation_id is provided
        if investigation_id:
            document_service.persist_document_metadata(
                db=db,
                extraction=extraction_result,
                investigation_id=investigation_id,
            )

        return extraction_result
    except DocumentProcessingError as err:
        # DocumentProcessingError subclasses are mapped by global error handler,
        # but re-raising allows standard routing
        raise err
    finally:
        await file.close()


@router.post(
    "/analyze",
    response_model=Union[NormalizedIncidentIntake, ExtractionAnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Preprocess incident intake content",
    description="Validates and normalizes multi-modal incident inputs (PDF extraction, narrative text, or email). If extract=true, orchestrates LangGraph incident extraction workflow.",
)
async def analyze_document(
    payload: DocumentAnalysisRequest,
    extract: bool = Query(default=False, description="Whether to trigger AI structured extraction"),
    raise_on_error: bool = Query(default=False, description="Whether to raise HTTP error on AI failure"),
):
    """Executes normalization and preparation across document, narrative text, or email intake channels."""
    try:
        normalized_intake = intake_service.prepare_intake(payload)
        if extract:
            response = run_incident_extraction_workflow(normalized_intake=normalized_intake)
            if raise_on_error and response.extraction_status == OverallExtractionStatus.FAILED:
                err_text = " ".join(response.warnings or []).lower()
                if "timeout" in err_text:
                    raise AITimeoutError(response.warnings[0] if response.warnings else "Groq request timed out.")
                elif "authentication" in err_text:
                    raise AIAuthenticationError(
                        response.warnings[0] if response.warnings else "Groq authentication failed."
                    )
            return response
        return normalized_intake
    except IncidentIntakeError as err:
        raise err


@router.post(
    "/extract",
    response_model=ExtractionAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured incident information using LangGraph",
    description="Executes normalization across document, narrative text, or email intake channels, then orchestrates LangGraph workflow nodes (input, extraction, validation, quality, finalization).",
)
async def extract_document_information(
    payload: DocumentAnalysisRequest,
    raise_on_error: bool = Query(
        default=False,
        description="Whether to raise HTTP error on upstream AI failure instead of returning FAILED status",
    ),
):
    """Executes normalization and orchestrates structured information extraction via LangGraph workflow."""
    try:
        normalized_intake = intake_service.prepare_intake(payload)
        response = run_incident_extraction_workflow(normalized_intake=normalized_intake)
        if raise_on_error and response.extraction_status == OverallExtractionStatus.FAILED:
            err_text = " ".join(response.warnings or []).lower()
            if "timeout" in err_text:
                raise AITimeoutError(response.warnings[0] if response.warnings else "Groq request timed out.")
            elif "authentication" in err_text:
                raise AIAuthenticationError(
                    response.warnings[0] if response.warnings else "Groq authentication failed."
                )
        return response
    except IncidentIntakeError as err:
        raise err
