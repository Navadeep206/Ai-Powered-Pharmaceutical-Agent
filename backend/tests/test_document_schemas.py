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
        # Selected DOCUMENT intake but did not supply document_id
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


def test_upload_pdf_contract_status():
    """Verify POST /api/documents/upload with valid PDF returns HTTP 501 Not Implemented."""
    files = {"file": ("batch_record_excursion.pdf", b"%PDF-1.4 simulated pdf bytes", "application/pdf")}
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 501
    assert "PDF document extraction pipeline" in response.json()["message"]


def test_analyze_document_endpoint_valid():
    """Verify POST /api/documents/analyze with valid payload returns HTTP 501 Not Implemented."""
    payload = {
        "intake_method": "Text",
        "text_input": {
            "title": "Deviation in Granulation Suite 2",
            "incident_text": "Impeller speed fluctuated between 100 rpm and 240 rpm during high-shear wet massing.",
        },
    }
    response = client.post("/api/documents/analyze", json=payload)
    assert response.status_code == 501
    assert "AI entity extraction workflow" in response.json()["message"]


def test_analyze_document_endpoint_invalid_payload():
    """Verify POST /api/documents/analyze with invalid payload returns HTTP 422 Unprocessable Entity."""
    payload = {
        "intake_method": "Text",
        # Missing text_input
    }
    response = client.post("/api/documents/analyze", json=payload)
    assert response.status_code == 422
