"""Pytest Configuration and Test Fixtures for RootIQ Backend."""

import io
from typing import List
import pytest
import pypdf
from fastapi.testclient import TestClient
from app.main import app


def build_pdf_with_text(pages_text: List[str]) -> bytes:
    """Helper to synthesize valid in-memory multi-page PDFs containing text streams."""
    writer = pypdf.PdfWriter()
    for text in pages_text:
        content_stream = f"BT /F1 12 Tf 72 712 Td ({text}) Tj ET".encode("latin-1")
        page_pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length {len(content_stream)} >>
stream
{content_stream.decode('latin-1')}
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000350 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
427
%%EOF
""".encode("latin-1")
        single_reader = pypdf.PdfReader(io.BytesIO(page_pdf))
        writer.add_page(single_reader.pages[0])

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def build_blank_pdf(num_pages: int = 1) -> bytes:
    """Helper to synthesize image-like or scanned PDFs containing zero text streams."""
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def valid_single_page_pdf() -> bytes:
    """Single page deviation incident PDF fixture."""
    return build_pdf_with_text([
        "Deviation DEV-2026-0891: Reactor R-102 temperature exceeded 78C limit reaching 84C."
    ])


@pytest.fixture
def valid_multi_page_pdf() -> bytes:
    """Multi-page technical investigation PDF fixture."""
    return build_pdf_with_text([
        "Batch Record 9942A: Stage 3 Friedel-Crafts acylation initiated at 08:30 UTC.",
        "Analytical In-Process Control: HPLC assay shows purity degraded to 92.4 percent.",
        "Maintenance Log: Valve CV-102 actuator inspected. Diaphragm showed severe mechanical tear.",
    ])


@pytest.fixture
def scanned_blank_pdf() -> bytes:
    """Scanned image PDF fixture with no digital text stream."""
    return build_blank_pdf(num_pages=2)
