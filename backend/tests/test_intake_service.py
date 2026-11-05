"""Tests for Incident Intake Service."""

import pytest
from app.core.exceptions import InvalidEmailInputError, InvalidIncidentTextError
from app.schemas.document import (
    DocumentAnalysisRequest,
    DocumentExtractionResult,
    EmailIncidentInput,
    IntakeMethodEnum,
    PageExtractionResult,
    TextIncidentInput,
)
from app.services.intake_service import intake_service


def test_process_valid_text_intake():
    """Verify processing and normalization of raw narrative text."""
    inp = TextIncidentInput(
        title="  Excursion during crystallization  ",
        incident_text="   Agitator motor halted abruptly during the addition of heptane anti-solvent.   \n\n  Temperature climbed by 4 degrees.  ",
        department="Purification",
    )
    result = intake_service.process_text_intake(inp)
    assert result.source_type == IntakeMethodEnum.TEXT
    assert result.processing_status == "Ready for AI Analysis"
    assert "Incident Title: Excursion during crystallization" in result.prepared_incident_text
    assert "Department: Purification" in result.prepared_incident_text
    assert "Agitator motor halted abruptly" in result.prepared_incident_text
    assert result.subject == "Excursion during crystallization"


def test_process_empty_text_intake_rejection():
    """Verify empty or whitespace-only text raises InvalidIncidentTextError."""
    inp = TextIncidentInput.model_construct(incident_text="   \n\t  ")
    with pytest.raises(InvalidIncidentTextError):
        intake_service.process_text_intake(inp)


def test_process_too_short_text_intake_rejection():
    """Verify text under 15 characters raises InvalidIncidentTextError."""
    inp = TextIncidentInput.model_construct(incident_text="Too short")
    with pytest.raises(InvalidIncidentTextError):
        intake_service.process_text_intake(inp)


def test_process_valid_email_intake():
    """Verify email normalization and preservation of subject and body."""
    inp = EmailIncidentInput(
        subject="  URGENT: Deviation in Batch 9942A  ",
        body="   Shift supervisor observed foreign black particulate matter on filter cloth during discharge.  ",
        sender="shift.lead@pharma.corp",
    )
    result = intake_service.process_email_intake(inp)
    assert result.source_type == IntakeMethodEnum.EMAIL
    assert result.subject == "URGENT: Deviation in Batch 9942A"
    assert "Subject: URGENT: Deviation in Batch 9942A" in result.prepared_incident_text
    assert "Sender: shift.lead@pharma.corp" in result.prepared_incident_text
    assert "foreign black particulate matter" in result.prepared_incident_text
    assert result.processing_status == "Ready for AI Analysis"


def test_process_empty_email_rejection():
    """Verify empty email subject or body raises InvalidEmailInputError."""
    inp1 = EmailIncidentInput.model_construct(subject="   ", body="Valid length body content.")
    with pytest.raises(InvalidEmailInputError):
        intake_service.process_email_intake(inp1)

    inp2 = EmailIncidentInput.model_construct(subject="Valid Subject", body="   \n\t  ")
    with pytest.raises(InvalidEmailInputError):
        intake_service.process_email_intake(inp2)


def test_process_pdf_intake():
    """Verify intake conversion from DocumentExtractionResult."""
    extraction = DocumentExtractionResult(
        document_id="DOC-TEST-1234",
        original_filename="batch_deviation.pdf",
        file_size_bytes=4096,
        number_of_pages=2,
        extracted_text="Page 1 text content.\n\nPage 2 technical narrative.",
        page_wise_content=[
            PageExtractionResult(page_number=1, text="Page 1 text content.", character_count=20, has_text=True, requires_ocr=False),
            PageExtractionResult(page_number=2, text="Page 2 technical narrative.", character_count=26, has_text=True, requires_ocr=False),
        ],
        extraction_status="Success",
        pages_requiring_ocr=[],
        warnings=[],
    )
    result = intake_service.process_pdf_intake(extraction)
    assert result.source_type == IntakeMethodEnum.DOCUMENT
    assert result.source_filename == "batch_deviation.pdf"
    assert len(result.page_references) == 2
    assert result.processing_status == "Ready for AI Analysis"
    assert "Page 1 text content." in result.prepared_incident_text


def test_prepare_intake_dispatch():
    """Verify prepare_intake dispatches correctly to respective handlers."""
    # Text dispatch
    req_text = DocumentAnalysisRequest(
        intake_method=IntakeMethodEnum.TEXT,
        text_input=TextIncidentInput(incident_text="Valid narrative detail describing deviation."),
    )
    res_text = intake_service.prepare_intake(req_text)
    assert res_text.source_type == IntakeMethodEnum.TEXT

    # Email dispatch
    req_email = DocumentAnalysisRequest(
        intake_method=IntakeMethodEnum.EMAIL,
        email_input=EmailIncidentInput(subject="Deviation alert", body="Valid narrative detail describing deviation."),
    )
    res_email = intake_service.prepare_intake(req_email)
    assert res_email.source_type == IntakeMethodEnum.EMAIL
