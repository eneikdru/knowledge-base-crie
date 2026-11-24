"""Tests for admission SQLite schema, 11-PDF deduplication, rollback, and idempotency.

Note: crie_document_parser.py and crie_persistent_memory.py are outside the
declared file scope for this slice, so this module defines and verifies the
target SQLite DDL and ingestion contract directly via Python stdlib + pytest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
import sqlite3
from typing import Iterable

import pytest


SQL_CREATE_UPLOADED_DOCUMENTS = """
CREATE TABLE IF NOT EXISTS uploaded_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    content_sha256 TEXT NOT NULL UNIQUE
)
"""

SQL_CREATE_ADMISSION_RECORDS = """
CREATE TABLE IF NOT EXISTS admission_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    order_number TEXT NOT NULL,
    order_date TEXT NOT NULL,
    education_level TEXT NOT NULL CHECK (education_level IN ('ординатура', 'аспирантура')),
    specialty_code TEXT NOT NULL,
    specialty_name TEXT NOT NULL,
    financing_type TEXT NOT NULL CHECK (financing_type IN ('бюджет', 'целевая квота', 'договор')),
    admission_stage TEXT NOT NULL CHECK (admission_stage IN ('основной', 'допконкурс')),
    enrolled_count INTEGER NOT NULL CHECK (enrolled_count >= 0),
    student_identifiers_json TEXT NOT NULL,
    FOREIGN KEY (doc_id) REFERENCES uploaded_documents(id) ON DELETE CASCADE
)
"""

ORDER_RE = re.compile(r"Приказ\s+№\s*(?P<number>[\w\-/]+)\s+от\s+(?P<date>\d{4}-\d{2}-\d{2})")
ROW_RE = re.compile(
    r"^(?P<level>ординатура|аспирантура)\s*\|\s*"
    r"(?P<code>\d{2}\.\d{2}\.\d{2})\s*\|\s*"
    r"(?P<name>[^|]+?)\s*\|\s*"
    r"(?P<financing>бюджет|целевая квота|договор)\s*\|\s*"
    r"(?P<stage>основной|допконкурс)\s*\|\s*"
    r"(?P<count>\d+)\s*\|\s*"
    r"(?P<ids>[^\n]+)$",
    re.MULTILINE,
)


class DocumentParseError(Exception):
    """Raised when a PDF payload is corrupted or lacks recognizable admission data."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


@dataclass(frozen=True)
class ParsedAdmissionRecord:
    order_number: str
    order_date: str
    education_level: str
    specialty_code: str
    specialty_name: str
    financing_type: str
    admission_stage: str
    enrolled_count: int
    student_identifiers: list[str]


@dataclass(frozen=True)
class IngestionDiagnostic:
    filename: str
    error_code: str
    message: str


@dataclass
class BatchIngestionResult:
    inserted_docs: int = 0
    skipped_duplicates: list[str] = field(default_factory=list)
    inserted_records: int = 0
    diagnostics: list[IngestionDiagnostic] = field(default_factory=list)


def init_schema(conn: sqlite3.Connection) -> None:
    """Creates uploaded_documents and admission_records tables if absent."""
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(SQL_CREATE_UPLOADED_DOCUMENTS)
    conn.execute(SQL_CREATE_ADMISSION_RECORDS)
    conn.commit()


def infer_doc_type(filename: str) -> str:
    """Maps filename prefix to canonical document type."""
    if filename.startswith("Svedeniya_o_zachislenii_"):
        return "zachislenie"
    if filename.startswith("Svedeniya_o_prieme_"):
        return "priem"
    raise DocumentParseError("UNRECOGNIZED_DOCUMENT_TYPE", f"Unsupported filename: {filename}")


def compute_content_hash(raw_text: str) -> str:
    """Computes a normalized SHA-256 hash for duplicate detection."""
    normalized = re.sub(r"\s+", " ", raw_text.strip()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def extract_pdf_text(payload: bytes) -> str:
    """Validates a minimal PDF payload and extracts UTF-8 text lines."""
    if not payload.startswith(b"%PDF-") or b"%%EOF" not in payload:
        raise DocumentParseError("CORRUPTED_PDF", "Missing PDF header or EOF marker")
    start_marker = b"BT\n"
    end_marker = b"\nET"
    start = payload.find(start_marker)
    end = payload.find(end_marker)
    if start == -1 or end == -1 or end <= start:
        raise DocumentParseError("UNRECOGNIZED_PDF_CONTENT", "No text stream found in PDF")
    text_bytes = payload[start + len(start_marker) : end]
    try:
        text = text_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentParseError("CORRUPTED_PDF_ENCODING", f"Invalid UTF-8 text: {exc}") from exc
    if not text.strip():
        raise DocumentParseError("EMPTY_PDF_TEXT", "Extracted PDF text is empty")
    return text


def parse_admission_records(raw_text: str) -> list[ParsedAdmissionRecord]:
    """Extracts structured admission rows from normalized document text."""
    order_match = ORDER_RE.search(raw_text)
    if not order_match:
        raise DocumentParseError("UNRECOGNIZED_ORDER_HEADER", "Missing order number or date")
    order_number = order_match.group("number")
    order_date = order_match.group("date")

    records: list[ParsedAdmissionRecord] = []
    for match in ROW_RE.finditer(raw_text):
        student_ids = [item.strip() for item in match.group("ids").split(",") if item.strip()]
        enrolled_count = int(match.group("count"))
        if enrolled_count != len(student_ids):
            raise DocumentParseError(
                "COUNT_MISMATCH",
                f"Expected {enrolled_count} student IDs, found {len(student_ids)}",
            )
        records.append(
            ParsedAdmissionRecord(
                order_number=order_number,
                order_date=order_date,
                education_level=match.group("level"),
                specialty_code=match.group("code"),
                specialty_name=match.group("name").strip(),
                financing_type=match.group("financing"),
                admission_stage=match.group("stage"),
                enrolled_count=enrolled_count,
                student_identifiers=student_ids,
            )
        )
    if not records:
        raise DocumentParseError("NO_ADMISSION_ROWS", "No structured admission rows matched")
    return records


def ingest_pdf_batch(
    conn: sqlite3.Connection,
    documents: Iterable[tuple[str, bytes]],
    uploaded_at: str,
) -> BatchIngestionResult:
    """Ingests a batch of PDFs with SHA-256 deduplication and per-file rollback."""
    result = BatchIngestionResult()
    for filename, payload in documents:
        try:
            doc_type = infer_doc_type(filename)
            raw_text = extract_pdf_text(payload)
            content_hash = compute_content_hash(raw_text)

            existing = conn.execute(
                "SELECT filename FROM uploaded_documents WHERE content_sha256 = ?",
                (content_hash,),
            ).fetchone()
            if existing is not None:
                result.skipped_duplicates.append(filename)
                continue

            records = parse_admission_records(raw_text)

            conn.execute("BEGIN")
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO uploaded_documents (filename, uploaded_at, raw_text, doc_type, content_sha256)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (filename, uploaded_at, raw_text, doc_type, content_hash),
                )
                doc_id = cursor.lastrowid
                for rec in records:
                    conn.execute(
                        """
                        INSERT INTO admission_records (
                            doc_id, order_number, order_date, education_level,
                            specialty_code, specialty_name, financing_type,
                            admission_stage, enrolled_count, student_identifiers_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            doc_id,
                            rec.order_number,
                            rec.order_date,
                            rec.education_level,
                            rec.specialty_code,
                            rec.specialty_name,
                            rec.financing_type,
                            rec.admission_stage,
                            rec.enrolled_count,
                            json.dumps(rec.student_identifiers, ensure_ascii=False),
                        ),
                    )
                conn.commit()
                result.inserted_docs += 1
                result.inserted_records += len(records)
            except Exception:
                conn.rollback()
                raise
        except DocumentParseError as exc:
            result.diagnostics.append(
                IngestionDiagnostic(
                    filename=filename,
                    error_code=exc.error_code,
                    message=exc.message,
                )
            )
    return result


def _build_pdf(body_text: str) -> bytes:
    return f"%PDF-1.4\n1 0 obj\nBT\n{body_text}\nET\n%%EOF\n".encode("utf-8")


def _build_eleven_pdf_fixture() -> list[tuple[str, bytes]]:
    """Builds 11 realistic PDFs where files [1], [10], and [11] are duplicates."""
    shared_duplicate_text = (
        "Приказ № 101-О от 2026-08-15\n"
        "ординатура | 31.08.01 | Акушерство и гинекология | бюджет | основной | 2 | ID-001, ID-002\n"
        "ординатура | 31.08.49 | Терапия | целевая квота | основной | 1 | ID-003"
    )
    duplicate_with_whitespace = shared_duplicate_text.replace(" | ", "   |   ")

    specs = [
        ("Svedeniya_o_zachislenii_01.pdf", shared_duplicate_text),
        (
            "Svedeniya_o_zachislenii_02.pdf",
            "Приказ № 102-О от 2026-08-16\n"
            "ординатура | 31.08.67 | Хирургия | бюджет | основной | 2 | ID-004, ID-005",
        ),
        (
            "Svedeniya_o_zachislenii_03.pdf",
            "Приказ № 103-О от 2026-08-17\n"
            "ординатура | 31.08.19 | Педиатрия | договор | основной | 1 | ID-006",
        ),
        (
            "Svedeniya_o_zachislenii_04.pdf",
            "Приказ № 104-О от 2026-08-18\n"
            "аспирантура | 30.06.01 | Фундаментальная медицина | бюджет | основной | 2 | ID-007, ID-008",
        ),
        (
            "Svedeniya_o_zachislenii_05.pdf",
            "Приказ № 105-О от 2026-08-19\n"
            "ординатура | 31.08.02 | Анестезиология-реаниматология | целевая квота | основной | 1 | ID-009",
        ),
        (
            "Svedeniya_o_prieme_06.pdf",
            "Приказ № 106-П от 2026-08-20\n"
            "ординатура | 31.08.57 | Онкология | бюджет | допконкурс | 2 | ID-010, ID-011",
        ),
        (
            "Svedeniya_o_prieme_07.pdf",
            "Приказ № 107-П от 2026-08-21\n"
            "аспирантура | 31.06.01 | Клиническая медицина | договор | допконкурс | 1 | ID-012",
        ),
        (
            "Svedeniya_o_prieme_08.pdf",
            "Приказ № 108-П от 2026-08-22\n"
            "ординатура | 31.08.42 | Неврология | бюджет | основной | 2 | ID-013, ID-014",
        ),
        (
            "Svedeniya_o_prieme_09.pdf",
            "Приказ № 109-П от 2026-08-23\n"
            "ординатура | 31.08.36 | Кардиология | целевая квота | допконкурс | 1 | ID-015",
        ),
        ("Svedeniya_o_zachislenii_10.pdf", shared_duplicate_text),
        ("Svedeniya_o_zachislenii_11.pdf", duplicate_with_whitespace),
    ]
    return [(name, _build_pdf(text)) for name, text in specs]


@pytest.fixture()
def db_conn(tmp_path) -> sqlite3.Connection:
    conn = sqlite3.connect(tmp_path / "crie_admissions.db")
    init_schema(conn)
    try:
        yield conn
    finally:
        conn.close()


def test_schema_creates_expected_tables_and_columns(db_conn: sqlite3.Connection) -> None:
    uploaded_cols = [
        row[1] for row in db_conn.execute("PRAGMA table_info(uploaded_documents)").fetchall()
    ]
    admission_cols = [
        row[1] for row in db_conn.execute("PRAGMA table_info(admission_records)").fetchall()
    ]
    assert uploaded_cols == [
        "id",
        "filename",
        "uploaded_at",
        "raw_text",
        "doc_type",
        "content_sha256",
    ]
    assert admission_cols == [
        "id",
        "doc_id",
        "order_number",
        "order_date",
        "education_level",
        "specialty_code",
        "specialty_name",
        "financing_type",
        "admission_stage",
        "enrolled_count",
        "student_identifiers_json",
    ]


def test_eleven_pdf_batch_deduplicates_1_10_11_and_populates_records(
    db_conn: sqlite3.Connection,
) -> None:
    batch = _build_eleven_pdf_fixture()
    result = ingest_pdf_batch(db_conn, batch, uploaded_at="2026-08-25T10:00:00Z")

    assert result.diagnostics == []
    assert result.inserted_docs == 9
    assert result.skipped_duplicates == [
        "Svedeniya_o_zachislenii_10.pdf",
        "Svedeniya_o_zachislenii_11.pdf",
    ]
    assert result.inserted_records == 10

    doc_count = db_conn.execute("SELECT COUNT(*) FROM uploaded_documents").fetchone()[0]
    rec_rows = db_conn.execute(
        """
        SELECT order_number, education_level, specialty_code, financing_type,
               admission_stage, enrolled_count, student_identifiers_json
        FROM admission_records
        """
    ).fetchall()

    assert doc_count == 9
    assert len(rec_rows) == 10
    for row in rec_rows:
        identifiers = json.loads(row[6])
        assert isinstance(identifiers, list)
        assert len(identifiers) == row[5]

    total_enrolled = sum(row[5] for row in rec_rows)
    assert total_enrolled == 15


def test_corrupted_or_unrecognized_pdf_records_diagnostic_without_partial_rows(
    db_conn: sqlite3.Connection,
) -> None:
    valid_pdf = _build_pdf(
        "Приказ № 201-О от 2026-08-24\n"
        "ординатура | 31.08.01 | Акушерство и гинекология | бюджет | основной | 1 | ID-101"
    )
    corrupted_pdf = b"NOT_A_VALID_PDF_STREAM"
    mismatched_count_pdf = _build_pdf(
        "Приказ № 202-О от 2026-08-24\n"
        "ординатура | 31.08.49 | Терапия | бюджет | основной | 3 | ID-102"
    )
    unrecognized_name_pdf = valid_pdf

    result = ingest_pdf_batch(
        db_conn,
        [
            ("Svedeniya_o_zachislenii_corrupt.pdf", corrupted_pdf),
            ("Svedeniya_o_zachislenii_mismatch.pdf", mismatched_count_pdf),
            ("unknown_document.pdf", unrecognized_name_pdf),
            ("Svedeniya_o_zachislenii_valid.pdf", valid_pdf),
        ],
        uploaded_at="2026-08-25T10:00:00Z",
    )

    assert result.inserted_docs == 1
    assert result.inserted_records == 1
    assert [(d.filename, d.error_code) for d in result.diagnostics] == [
        ("Svedeniya_o_zachislenii_corrupt.pdf", "CORRUPTED_PDF"),
        ("Svedeniya_o_zachislenii_mismatch.pdf", "COUNT_MISMATCH"),
        ("unknown_document.pdf", "UNRECOGNIZED_DOCUMENT_TYPE"),
    ]

    docs = db_conn.execute("SELECT filename FROM uploaded_documents").fetchall()
    assert docs == [("Svedeniya_o_zachislenii_valid.pdf",)]
    assert db_conn.execute("SELECT COUNT(*) FROM admission_records").fetchone()[0] == 1


def test_reexecution_is_idempotent_across_11_pdfs(db_conn: sqlite3.Connection) -> None:
    batch = _build_eleven_pdf_fixture()
    first_run = ingest_pdf_batch(db_conn, batch, uploaded_at="2026-08-25T10:00:00Z")
    second_run = ingest_pdf_batch(db_conn, batch, uploaded_at="2026-08-25T12:00:00Z")

    assert first_run.inserted_docs == 9
    assert second_run.inserted_docs == 0
    assert second_run.inserted_records == 0
    assert len(second_run.skipped_duplicates) == 11
    assert db_conn.execute("SELECT COUNT(*) FROM uploaded_documents").fetchone()[0] == 9
    assert db_conn.execute("SELECT COUNT(*) FROM admission_records").fetchone()[0] == 10
