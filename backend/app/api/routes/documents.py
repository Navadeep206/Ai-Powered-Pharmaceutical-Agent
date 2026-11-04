"""Document upload and AI intake analysis route definitions."""

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentAnalysisRequest,
)
from app.schemas.extraction import ExtractionAnalysisResponse

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an incident report PDF",
    description="Validates multipart PDF upload and verifies file structure.",
)
async def upload_document(file: UploadFile = File(...)):
    """Validates PDF file type and structure.

    Returns HTTP 501 Not Implemented for storage and extraction pipeline.
    """
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF documents (*.pdf) are accepted for incident intake.",
        )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="PDF document extraction pipeline will be implemented in subsequent phases.",
    )


@router.post(
    "/analyze",
    response_model=ExtractionAnalysisResponse,
    summary="Analyze incident narrative or document",
    description="Initiates AI extraction across document, raw narrative text, or email intake channels.",
)
async def analyze_document(payload: DocumentAnalysisRequest):
    """Scaffolding contract: Validates intake payload and method constraints.

    Returns HTTP 501 Not Implemented pending AI extraction agent integration.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="AI entity extraction workflow will be implemented in subsequent phases.",
    )

