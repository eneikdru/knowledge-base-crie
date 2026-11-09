"""Unit and integration tests for GOST R 7.0.97-2016 DOCX order generation."""

import zipfile
from io import BytesIO
import pytest
from docx import Document
from docx.shared import Mm
from fastapi.testclient import TestClient

from services.docx_order_generator import (
    build_order_docx,
    ROSPOTREBNADZOR_HEADER_LINES,
    ORDER_TEMPLATES,
)
from crie_assistant_api import app

client = TestClient(app)


def test_gost_page_margins_and_dimensions():
    """Verify 30mm left, 15mm right, 20mm top/bottom margins as mandated by GOST R 7.0.97-2016."""
    stream = build_order_docx("enrollment")
    doc = Document(stream)
    section = doc.sections[0]

    # Margin checks (tolerances within 0.5mm)
    left_mm = section.left_margin.mm
    right_mm = section.right_margin.mm
    top_mm = section.top_margin.mm
    bottom_mm = section.bottom_margin.mm

    assert abs(left_mm - 30.0) < 0.5, f"Left margin expected 30mm, got {left_mm}"
    assert abs(right_mm - 15.0) < 0.5, f"Right margin expected 15mm, got {right_mm}"
    assert abs(top_mm - 20.0) < 0.5, f"Top margin expected 20mm, got {top_mm}"
    assert abs(bottom_mm - 20.0) < 0.5, f"Bottom margin expected 20mm, got {bottom_mm}"


def test_rospotrebnadzor_requisites_rendered():
    """Verify Rospotrebnadzor institution header requisites are present."""
    stream = build_order_docx("enrollment", order_number="42-ОД")
    doc = Document(stream)
    full_text = " ".join(p.text for p in doc.paragraphs)

    for header_part in ROSPOTREBNADZOR_HEADER_LINES:
        assert header_part in full_text

    assert "ПРИКАЗ" in full_text
    assert "О зачислении на обучение" in full_text
    assert "В соответствии с Федеральным законом" in full_text
    assert "ПРИКАЗЫВАЮ:" in full_text


def test_docx_xml_integrity_and_validity():
    """Verify the returned document is a valid OOXML/ZIP package with well-formed word/document.xml."""
    stream = build_order_docx("gia_admission", order_number="105-ГИА")
    stream.seek(0)

    # Open as zip and inspect contents
    with zipfile.ZipFile(stream, "r") as z:
        assert "word/document.xml" in z.namelist()
        assert "[Content_Types].xml" in z.namelist()
        doc_xml = z.read("word/document.xml").decode("utf-8")
        assert "Times New Roman" in doc_xml
        assert "РОСПОТРЕБНАДЗОР" in doc_xml
        assert "ГИА" in doc_xml


def test_api_generate_order_endpoint_enrollment():
    """Test API endpoint /api/orders/generate for enrollment order."""
    payload = {
        "order_type": "enrollment",
        "order_number": "88-ОД",
        "order_date": "01 сентября 2026 г.",
        "specialty_code": "31.08.36",
        "specialty_name": "Эпидемиология",
        "protocol_num": "5",
        "protocol_date": "28 августа 2026 г.",
        "students": [
            {"identifier": "ORD-2026-101", "details": "конкурсный балл 100"},
            {"identifier": "ORD-2026-102", "details": "конкурсный балл 97"}
        ]
    }
    response = client.post("/api/orders/generate", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert "order_enrollment_88-ОД.docx" in response.headers["content-disposition"]

    # Load resulting bytes with docx parser to assert content
    doc = Document(BytesIO(response.content))
    text = " ".join(p.text for p in doc.paragraphs)
    assert "ORD-2026-101" in text
    assert "ORD-2026-102" in text
    assert "31.08.36" in text
    assert "Эпидемиология" in text


def test_api_generate_order_types_and_validation():
    """Test supported order types and invalid request rejection."""
    resp_types = client.get("/api/orders/types")
    assert resp_types.status_code == 200
    type_ids = [t["id"] for t in resp_types.json()["order_types"]]
    assert "enrollment" in type_ids
    assert "gia_admission" in type_ids
    assert "scholarship" in type_ids

    # Invalid order type returns 400
    bad_resp = client.post("/api/orders/generate", json={"order_type": "unknown_type"})
    assert bad_resp.status_code == 400
    assert "Invalid order_type" in bad_resp.json()["detail"]
