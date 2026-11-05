"""Tests for Document Processing Service."""

import pytest
from app.core.exceptions import (
    CorruptedPDFError,
    EmptyDocumentError,
    InvalidPDFFormatError,
    OversizedDocumentError,
)
from app.services.document_service import DocumentService, document_service
from tests.conftest import build_blank_pdf, build_pdf_with_text


def test_sanitize_filename():
    """Verify filename sanitization prevents directory traversal and malicious characters."""
    service = DocumentService()
    assert service.sanitize_filename("../../etc/passwd") == "passwd.pdf"
    assert service.sanitize_filename("batch_log?#1.pdf") == "batch_log__1.pdf"
    assert service.sanitize_filename(None) == "incident_document.pdf"
    assert service.sanitize_filename("test_doc") == "test_doc.pdf"


def test_extract_valid_single_page_pdf(valid_single_page_pdf):
    """Verify text extraction from a valid single page PDF."""
    result = document_service.extract_text_from_pdf_bytes(
        valid_single_page_pdf,
        filename="deviation_report.pdf",
    )
    assert result.number_of_pages == 1
    assert result.extraction_status == "Success"
    assert "Reactor R-102 temperature exceeded 78C" in result.extracted_text
    assert len(result.page_wise_content) == 1
    assert result.page_wise_content[0].page_number == 1
    assert result.page_wise_content[0].has_text is True
    assert result.page_wise_content[0].requires_ocr is False
    assert result.pages_requiring_ocr == []


def test_extract_valid_multi_page_pdf(valid_multi_page_pdf):
    """Verify multi-page PDF preserves page boundaries and page numbers."""
    result = document_service.extract_text_from_pdf_bytes(
        valid_multi_page_pdf,
        filename="investigation_dossier.pdf",
    )
    assert result.number_of_pages == 3
    assert result.extraction_status == "Success"
    assert "Batch Record 9942A" in result.extracted_text
    assert "HPLC assay shows purity degraded" in result.extracted_text
    assert "Valve CV-102 actuator inspected" in result.extracted_text
    assert len(result.page_wise_content) == 3
    assert result.page_wise_content[0].page_number == 1
    assert result.page_wise_content[1].page_number == 2
    assert result.page_wise_content[2].page_number == 3


def test_scanned_pdf_ocr_detection(scanned_blank_pdf):
    """Verify detection of image-only or scanned PDFs requiring OCR."""
    result = document_service.extract_text_from_pdf_bytes(
        scanned_blank_pdf,
        filename="scanned_batch_sheet.pdf",
    )
    assert result.number_of_pages == 2
    assert result.extraction_status == "OCR Required"
    assert result.pages_requiring_ocr == [1, 2]
    assert any("OCR is required" in w for w in result.warnings)


def test_partial_scanned_pdf_ocr_detection():
    """Verify mixed PDF with digital and scanned pages flags partial OCR requirement."""
    # Build PDF where page 1 has text and page 2 is blank
    p1 = build_pdf_with_text(["Page 1 digital text"])
    p2 = build_blank_pdf(1)
    
    import io, pypdf
    writer = pypdf.PdfWriter()
    writer.add_page(pypdf.PdfReader(io.BytesIO(p1)).pages[0])
    writer.add_page(pypdf.PdfReader(io.BytesIO(p2)).pages[0])
    buf = io.BytesIO()
    writer.write(buf)
    mixed_bytes = buf.getvalue()

    result = document_service.extract_text_from_pdf_bytes(mixed_bytes, "mixed.pdf")
    assert result.number_of_pages == 2
    assert result.extraction_status == "Partial Extraction (OCR Required)"
    assert result.pages_requiring_ocr == [2]
    assert result.page_wise_content[0].has_text is True
    assert result.page_wise_content[1].requires_ocr is True


def test_empty_bytes_rejection():
    """Verify empty byte payload raises EmptyDocumentError."""
    with pytest.raises(EmptyDocumentError):
        document_service.extract_text_from_pdf_bytes(b"", "empty.pdf")


def test_invalid_format_signature_rejection():
    """Verify non-PDF bytes without %PDF- signature raise InvalidPDFFormatError."""
    with pytest.raises(InvalidPDFFormatError):
        document_service.extract_text_from_pdf_bytes(
            b"Plain text file that is not a PDF",
            "fake.pdf",
        )


def test_invalid_extension_rejection(valid_single_page_pdf):
    """Verify file without .pdf extension is rejected."""
    with pytest.raises(InvalidPDFFormatError):
        document_service.extract_text_from_pdf_bytes(
            valid_single_page_pdf,
            "document.docx",
        )


def test_oversized_byte_rejection(valid_single_page_pdf):
    """Verify file exceeding size limit raises OversizedDocumentError."""
    # Test service with 100 byte limit
    small_service = DocumentService(max_file_size_bytes=100)
    with pytest.raises(OversizedDocumentError):
        small_service.extract_text_from_pdf_bytes(valid_single_page_pdf, "large.pdf")


def test_corrupted_pdf_rejection():
    """Verify broken PDF structure raises CorruptedPDFError."""
    corrupted_bytes = b"%PDF-1.4\n1 0 obj << random damaged syntax >>"
    with pytest.raises(CorruptedPDFError):
        document_service.extract_text_from_pdf_bytes(corrupted_bytes, "corrupt.pdf")


def test_normalize_extracted_text():
    """Verify whitespace cleanup preserves intentional paragraph breaks."""
    raw = "  Line 1   with   spaces  \r\n\r\n\r\nLine 2 after multi breaks \t\t with tabs  "
    normalized = document_service.normalize_extracted_text(raw)
    assert "Line 1 with spaces\n\nLine 2 after multi breaks with tabs" in normalized
