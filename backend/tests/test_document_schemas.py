"""Tests for Document and multi-modal intake schemas and routes."""

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.document import (
    IntakeMethodEnum,
    DocumentAnalysisRequest,
    TextIncidentInput,
    EmailIncidentInput,
)
from tests.conftest import build_pdf_with_text

client = TestClient(app)


def test_valid_document_analysis_request():
    """Verify DocumentAnalysisRequest with matching document_id passes validation."""
    req = DocumentAnalysisRequest(
        intake_method=IntakeMethodEnum.DOCUMENT,
        document_id="DOC-UUID-2026-9941",
    )
    assert req.intake_method == IntakeMethodEnum.DOCUMENT
    assert req.document_id == "DOC-UUID-2026-9941"


def test_valid_text_analysis_request():
    """Verify DocumentAnalysisRequest with text_input passes validation."""
    req = DocumentAnalysisRequest(
        intake_method=IntakeMethodEnum.TEXT,
        text_input=TextIncidentInput(
            title="Cooling loop failure in Reactor R-102",
            incident_text="During stage 3 synthesis, cooling water loop pressure plummeted to zero causing an excursion.",
            department="Synthesis",
        ),
    )
    assert req.intake_method == IntakeMethodEnum.TEXT
    assert "cooling water loop" in req.text_input.incident_text


def test_valid_email_analysis_request():
    """Verify DocumentAnalysisRequest with email_input passes validation."""
    req = DocumentAnalysisRequest(
        intake_method=IntakeMethodEnum.EMAIL,
        email_input=EmailIncidentInput(
            subject="URGENT: Deviation in Batch 9942A",
            body="Shift supervisor reported unexplained crystallization onset prior to anti-solvent addition.",
            sender="supervisor@pharma.corp",
        ),
    )
    assert req.intake_method == IntakeMethodEnum.EMAIL
    assert req.email_input.subject.startswith("URGENT")


def test_mismatched_intake_method_rejection():
    """Verify that specifying an intake method without providing its required sub-payload raises an error."""
    with pytest.raises(ValidationError):
        # Selected DOCUMENT intake but did not supply document_id or document_text
        DocumentAnalysisRequest(intake_method=IntakeMethodEnum.DOCUMENT)

    with pytest.raises(ValidationError):
        # Selected TEXT intake but did not supply text_input
        DocumentAnalysisRequest(intake_method=IntakeMethodEnum.TEXT)

    with pytest.raises(ValidationError):
        # Selected EMAIL intake but did not supply email_input
        DocumentAnalysisRequest(intake_method=IntakeMethodEnum.EMAIL)


# --- Document Endpoint Tests ---


def test_upload_non_pdf_rejection():
    """Verify POST /api/documents/upload rejects non-PDF files with HTTP 400 Bad Request."""
    files = {"file": ("deviation_notes.txt", b"Plain text deviation notes", "text/plain")}
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 400
    assert "Only PDF documents" in response.json()["message"]


def test_upload_pdf_real_extraction():
    """Verify POST /api/documents/upload extracts real PDF text in-memory."""
    pdf_bytes = build_pdf_with_text([
        "Deviation DEV-2026-0891: Reactor R-102 temperature exceeded 78C limit reaching 84C."
    ])
    files = {"file": ("batch_record_excursion.pdf", pdf_bytes, "application/pdf")}
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["number_of_pages"] == 1
    assert data["extraction_status"] == "Success"
    assert "Reactor R-102 temperature exceeded 78C" in data["extracted_text"]
    assert len(data["page_wise_content"]) == 1
    assert data["page_wise_content"][0]["page_number"] == 1


def test_analyze_document_endpoint_valid_text():
    """Verify POST /api/documents/analyze normalizes text intake and provides GxP disclaimer."""
    payload = {
        "intake_method": "Text",
        "text_input": {
            "title": "Deviation in Granulation Suite 2",
            "incident_text": "Impeller speed fluctuated between 100 rpm and 240 rpm during high-shear wet massing.",
        },
    }
    response = client.post("/api/documents/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["source_type"] == "Text"
    assert "Impeller speed fluctuated" in data["prepared_incident_text"]
    assert data["processing_status"] == "Ready for AI Analysis"
    assert "AI entity extraction has NOT yet been executed" in data["disclaimer"]


def test_analyze_document_endpoint_valid_email():
    """Verify POST /api/documents/analyze normalizes email intake."""
    payload = {
        "intake_method": "Email",
        "email_input": {
            "subject": "Deviation in Batch 8821",
            "body": "Operator noted white particulate accumulation in inline 0.2 micron sterile filter.",
            "sender": "qa.inspector@pharma.corp",
        },
    }
    response = client.post("/api/documents/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["source_type"] == "Email"
    assert data["subject"] == "Deviation in Batch 8821"
    assert "qa.inspector@pharma.corp" in data["prepared_incident_text"]


def test_analyze_document_endpoint_invalid_payload():
    """Verify POST /api/documents/analyze with invalid payload returns HTTP 422 Unprocessable Entity."""
    payload = {
        "intake_method": "Text",
        # Missing text_input
    }
    response = client.post("/api/documents/analyze", json=payload)
    assert response.status_code == 422
