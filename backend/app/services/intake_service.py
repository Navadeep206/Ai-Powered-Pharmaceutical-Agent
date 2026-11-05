"""Incident Intake Service for RootIQ.

Normalizes multi-modal incident intake (PDF extraction results, pasted narratives,
and email reports) into a uniform, verified preprocessed format ready for AI reasoning.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional
from app.core.exceptions import (
    InvalidEmailInputError,
    InvalidIncidentTextError,
)
from app.core.logging import get_logger
from app.schemas.document import (
    DocumentAnalysisRequest,
    DocumentExtractionResult,
    EmailIncidentInput,
    IntakeMethodEnum,
    NormalizedIncidentIntake,
    PageReference,
    TextIncidentInput,
)

logger = get_logger("services.intake")


class IntakeService:
    """Service preparing and standardizing multi-modal incident inputs."""

    def normalize_text(self, text: Optional[str]) -> str:
        """Strip extraneous whitespace while preserving intentional paragraph breaks."""
        if not text:
            return ""

        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
        joined = "\n".join(lines)
        return re.sub(r"\n{3,}", "\n\n", joined).strip()

    def process_pdf_intake(
        self,
        extraction_result: DocumentExtractionResult,
    ) -> NormalizedIncidentIntake:
        """Standardize a completed PDF extraction result into normalized incident intake."""
        page_refs = [
            PageReference(
                page_number=p.page_number,
                character_count=p.character_count,
                has_text=p.has_text,
                requires_ocr=p.requires_ocr,
            )
            for p in extraction_result.page_wise_content
        ]

        warnings = list(extraction_result.warnings)
        has_text = len(extraction_result.extracted_text.strip()) > 0

        if not has_text:
            warnings.append("No extractable digital text found in source document. OCR is recommended.")
            status = "Preprocessing Completed (OCR Recommended)"
            prepared_text = f"[NO EXTRACTABLE TEXT DETECTED IN PDF: {extraction_result.original_filename}]"
        else:
            status = "Ready for AI Analysis"
            prepared_text = extraction_result.extracted_text

        intake_id = f"INTAKE-DOC-{uuid.uuid4().hex[:10].upper()}"

        return NormalizedIncidentIntake(
            intake_id=intake_id,
            source_type=IntakeMethodEnum.DOCUMENT,
            source_filename=extraction_result.original_filename,
            subject=f"Document Intake: {extraction_result.original_filename}",
            prepared_incident_text=prepared_text,
            page_references=page_refs,
            processing_warnings=warnings,
            processing_status=status,
            processed_at=datetime.now(timezone.utc),
        )

    def process_text_intake(
        self,
        text_input: TextIncidentInput,
    ) -> NormalizedIncidentIntake:
        """Validate and normalize raw pasted narrative text."""
        raw_text = text_input.incident_text
        if not raw_text or not raw_text.strip():
            raise InvalidIncidentTextError("Incident text cannot be empty or contain only whitespace.")

        normalized_text = self.normalize_text(raw_text)
        if len(normalized_text) < 15:
            raise InvalidIncidentTextError(
                "Incident text is too brief to constitute a verifiable quality deviation narrative (minimum 15 characters)."
            )

        title = self.normalize_text(text_input.title) if text_input.title else None
        subject = title if title else "Pasted Incident Narrative"

        # Prepend title and department if supplied for context
        header_parts = []
        if title:
            header_parts.append(f"Incident Title: {title}")
        if text_input.department:
            header_parts.append(f"Department: {text_input.department.strip()}")

        if header_parts:
            prepared_text = "\n".join(header_parts) + "\n\n" + normalized_text
        else:
            prepared_text = normalized_text

        intake_id = f"INTAKE-TXT-{uuid.uuid4().hex[:10].upper()}"

        return NormalizedIncidentIntake(
            intake_id=intake_id,
            source_type=IntakeMethodEnum.TEXT,
            source_filename=None,
            subject=subject,
            prepared_incident_text=prepared_text,
            page_references=[],
            processing_warnings=[],
            processing_status="Ready for AI Analysis",
            processed_at=datetime.now(timezone.utc),
        )

    def process_email_intake(
        self,
        email_input: EmailIncidentInput,
    ) -> NormalizedIncidentIntake:
        """Validate and normalize email subject and body content."""
        raw_subject = email_input.subject
        raw_body = email_input.body

        if not raw_subject or not raw_subject.strip():
            raise InvalidEmailInputError("Email subject cannot be empty.")
        if not raw_body or not raw_body.strip():
            raise InvalidEmailInputError("Email body cannot be empty or contain only whitespace.")

        normalized_subject = self.normalize_text(raw_subject)
        normalized_body = self.normalize_text(raw_body)

        if len(normalized_body) < 15:
            raise InvalidEmailInputError(
                "Email body must provide sufficient technical detail (minimum 15 characters)."
            )

        header_lines = [f"Subject: {normalized_subject}"]
        if email_input.sender and email_input.sender.strip():
            header_lines.append(f"Sender: {email_input.sender.strip()}")

        prepared_text = "\n".join(header_lines) + "\n\nBody:\n" + normalized_body
        intake_id = f"INTAKE-EML-{uuid.uuid4().hex[:10].upper()}"

        return NormalizedIncidentIntake(
            intake_id=intake_id,
            source_type=IntakeMethodEnum.EMAIL,
            source_filename=None,
            subject=normalized_subject,
            prepared_incident_text=prepared_text,
            page_references=[],
            processing_warnings=[],
            processing_status="Ready for AI Analysis",
            processed_at=datetime.now(timezone.utc),
        )

    def prepare_intake(
        self,
        request: DocumentAnalysisRequest,
    ) -> NormalizedIncidentIntake:
        """Dispatch intake request to specific handler based on intake method."""
        if request.intake_method == IntakeMethodEnum.TEXT:
            if not request.text_input:
                raise InvalidIncidentTextError("Text input payload is required for text intake.")
            return self.process_text_intake(request.text_input)

        elif request.intake_method == IntakeMethodEnum.EMAIL:
            if not request.email_input:
                raise InvalidEmailInputError("Email input payload is required for email intake.")
            return self.process_email_intake(request.email_input)

        elif request.intake_method == IntakeMethodEnum.DOCUMENT:
            # If document_text was passed directly
            if request.document_text:
                normalized = self.normalize_text(request.document_text)
                return NormalizedIncidentIntake(
                    intake_id=f"INTAKE-DOC-{uuid.uuid4().hex[:10].upper()}",
                    source_type=IntakeMethodEnum.DOCUMENT,
                    source_filename=f"{request.document_id or 'document'}.pdf",
                    subject=f"Document Intake: {request.document_id or 'Document'}",
                    prepared_incident_text=normalized,
                    page_references=[],
                    processing_warnings=[],
                    processing_status="Ready for AI Analysis",
                    processed_at=datetime.now(timezone.utc),
                )
            else:
                # Document ID referenced without text stream
                doc_id = request.document_id or "UNKNOWN"
                return NormalizedIncidentIntake(
                    intake_id=f"INTAKE-DOC-{uuid.uuid4().hex[:10].upper()}",
                    source_type=IntakeMethodEnum.DOCUMENT,
                    source_filename=f"{doc_id}.pdf",
                    subject=f"Document Reference: {doc_id}",
                    prepared_incident_text=f"[Document Reference: {doc_id}]",
                    page_references=[],
                    processing_warnings=[
                        "Document ID referenced. Full document text will be retrieved from persistent storage in future phase."
                    ],
                    processing_status="Ready for AI Analysis",
                    processed_at=datetime.now(timezone.utc),
                )

        raise ValueError(f"Unsupported intake method '{request.intake_method}'")


# Singleton service instance
intake_service = IntakeService()
