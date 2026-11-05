"""Document Processing Service for RootIQ.

Handles PDF parsing, text extraction, page-wise boundary preservation,
OCR necessity detection, and GxP data integrity checks using pypdf.
"""

import io
import os
import re
import uuid
from typing import List, Optional, Tuple
import pypdf
from pypdf.errors import PdfReadError, PdfStreamError
from app.core.exceptions import (
    CorruptedPDFError,
    EmptyDocumentError,
    InvalidPDFFormatError,
    OversizedDocumentError,
    PasswordProtectedPDFError,
)
from app.core.logging import get_logger
from app.schemas.document import DocumentExtractionResult, PageExtractionResult

logger = get_logger("services.document")

# Default service constraints
DEFAULT_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_MAX_PAGE_COUNT = 100
PDF_MAGIC_BYTES = b"%PDF-"


class DocumentService:
    """Service encapsulating safe PDF validation, in-memory extraction, and OCR detection."""

    def __init__(
        self,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        max_page_count: int = DEFAULT_MAX_PAGE_COUNT,
    ):
        self.max_file_size_bytes = max_file_size_bytes
        self.max_page_count = max_page_count

    def sanitize_filename(self, filename: Optional[str]) -> str:
        """Sanitize client-supplied filename to prevent path traversal or malicious characters."""
        if not filename:
            return "incident_document.pdf"

        # Extract only the base name (strip directory paths)
        base = os.path.basename(filename)
        # Strip dangerous characters and directory separators
        clean = re.sub(r"[^\w\.\-\_]", "_", base)
        # Guarantee .pdf extension
        if not clean.lower().endswith(".pdf"):
            clean = f"{clean}.pdf"
        return clean

    def validate_pdf_bytes(self, file_bytes: bytes, filename: Optional[str] = None) -> None:
        """Validate raw byte content for size, format signature, and empty payloads."""
        if not file_bytes or len(file_bytes) == 0:
            raise EmptyDocumentError("The uploaded file is empty (0 bytes).")

        if len(file_bytes) > self.max_file_size_bytes:
            mb_limit = self.max_file_size_bytes // (1024 * 1024)
            raise OversizedDocumentError(
                f"Document exceeds maximum allowable file size of {mb_limit} MB."
            )

        if not file_bytes.startswith(PDF_MAGIC_BYTES):
            raise InvalidPDFFormatError(
                "Invalid PDF format. File content header does not start with valid PDF signature '%PDF-'."
            )

        if filename and not filename.lower().endswith(".pdf"):
            raise InvalidPDFFormatError(
                "Invalid file extension. Only files ending with '.pdf' are accepted."
            )

    def normalize_extracted_text(self, text: Optional[str]) -> str:
        """Normalize extracted text by cleaning excessive whitespace while preserving paragraphs."""
        if not text:
            return ""

        # Normalize line endings to \n
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace non-breaking spaces and tabs with standard space
        text = text.replace("\xa0", " ").replace("\t", " ")

        # Collapse 3 or more consecutive newlines into 2 (paragraph break)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Collapse horizontal whitespace runs while preserving line breaks
        lines = [re.sub(r"[ ]{2,}", " ", line).strip() for line in text.split("\n")]

        # Re-join lines
        normalized = "\n".join(lines)
        # Re-collapse blank lines created by empty stripped lines
        normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
        return normalized

    def extract_text_from_pdf_bytes(
        self,
        file_bytes: bytes,
        filename: Optional[str] = None,
    ) -> DocumentExtractionResult:
        """Extract text from in-memory PDF bytes with page tracking and OCR detection."""
        self.validate_pdf_bytes(file_bytes, filename)
        safe_filename = self.sanitize_filename(filename)

        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        except (PdfReadError, PdfStreamError, ValueError) as err:
            logger.warning("Corrupted or malformed PDF encountered: %s", str(err))
            raise CorruptedPDFError(
                "The uploaded PDF is malformed, damaged, or cannot be parsed by the PDF engine."
            )
        except Exception as err:
            logger.error("Unexpected error reading PDF structure: %s", str(err), exc_info=True)
            raise CorruptedPDFError("Unable to parse the PDF document structure.")

        # Check for encryption
        if reader.is_encrypted:
            try:
                # Attempt empty password decryption
                decrypted = reader.decrypt("")
                if not decrypted:
                    raise PasswordProtectedPDFError(
                        "The uploaded PDF is password-protected and cannot be extracted."
                    )
            except Exception:
                raise PasswordProtectedPDFError(
                    "The uploaded PDF is password-protected and cannot be extracted."
                )

        page_count = len(reader.pages)
        if page_count == 0:
            raise EmptyDocumentError("The uploaded PDF contains zero pages.")

        if page_count > self.max_page_count:
            raise OversizedDocumentError(
                f"Document exceeds maximum page limit of {self.max_page_count} pages (contains {page_count} pages)."
            )

        page_results: List[PageExtractionResult] = []
        pages_requiring_ocr: List[int] = []
        warnings: List[str] = []
        consolidated_text_parts: List[str] = []

        for idx, page in enumerate(reader.pages):
            page_number = idx + 1
            raw_text = ""
            try:
                raw_text = page.extract_text() or ""
            except Exception as page_err:
                logger.warning("Error extracting text on page %d: %s", page_number, str(page_err))
                warnings.append(f"Failed to read content stream on page {page_number}.")

            normalized = self.normalize_extracted_text(raw_text)
            has_text = len(normalized.strip()) > 0
            requires_ocr = not has_text

            if requires_ocr:
                pages_requiring_ocr.append(page_number)

            page_result = PageExtractionResult(
                page_number=page_number,
                text=normalized,
                character_count=len(normalized),
                has_text=has_text,
                requires_ocr=requires_ocr,
            )
            page_results.append(page_result)

            if has_text:
                consolidated_text_parts.append(
                    f"--- [Page {page_number}] ---\n{normalized}"
                )

        # Determine extraction lifecycle status
        if len(pages_requiring_ocr) == page_count:
            extraction_status = "OCR Required"
            warnings.append(
                "Document appears to be a scanned or image-only PDF. OCR is required to extract text."
            )
        elif len(pages_requiring_ocr) > 0:
            extraction_status = "Partial Extraction (OCR Required)"
            warnings.append(
                f"Pages {pages_requiring_ocr} contain no digital text stream and may require OCR."
            )
        else:
            extraction_status = "Success"

        full_text = "\n\n".join(consolidated_text_parts)

        doc_result = DocumentExtractionResult(
            document_id=f"DOC-{uuid.uuid4().hex[:12].upper()}",
            original_filename=safe_filename,
            file_size_bytes=len(file_bytes),
            number_of_pages=page_count,
            extracted_text=full_text,
            page_wise_content=page_results,
            extraction_status=extraction_status,
            pages_requiring_ocr=pages_requiring_ocr,
            warnings=warnings,
        )

        logger.info(
            "Extracted PDF '%s': %d pages, %d chars, status='%s'",
            safe_filename,
            page_count,
            len(full_text),
            extraction_status,
        )
        return doc_result


# Singleton service instance
document_service = DocumentService()
