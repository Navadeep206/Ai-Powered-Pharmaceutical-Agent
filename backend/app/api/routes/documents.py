"""Document upload and incident intake route definitions."""

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from app.core.exceptions import DocumentProcessingError, IncidentIntakeError
from app.schemas.document import (
    DocumentAnalysisRequest,
    DocumentExtractionResult,
    NormalizedIncidentIntake,
)
from app.services.document_service import document_service
from app.services.intake_service import intake_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentExtractionResult,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and extract text from an incident PDF",
    description="Validates multipart PDF file structure, extracts text page-by-page, and detects scanned pages requiring OCR.",
)
async def upload_document(file: UploadFile = File(...)):
    """Validates PDF file, extracts text in-memory, and detects OCR necessity without permanent storage."""
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
        return extraction_result
    except DocumentProcessingError as err:
        # DocumentProcessingError subclasses are mapped by global error handler,
        # but re-raising allows standard routing
        raise err
    finally:
        await file.close()


@router.post(
    "/analyze",
    response_model=NormalizedIncidentIntake,
    status_code=status.HTTP_200_OK,
    summary="Preprocess incident intake content",
    description="Validates and normalizes multi-modal incident inputs (PDF extraction, narrative text, or email). NOTE: AI entity extraction is pending future phases; returned content represents verified preprocessed source text.",
)
async def analyze_document(payload: DocumentAnalysisRequest):
    """Executes normalization and preparation across document, narrative text, or email intake channels."""
    try:
        normalized_intake = intake_service.prepare_intake(payload)
        return normalized_intake
    except IncidentIntakeError as err:
        raise err
