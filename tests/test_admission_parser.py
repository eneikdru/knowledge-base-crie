"""Tests for admission PDF schema, structured extraction, deduplication, and error handling."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List, Optional

import pytest


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS uploaded_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS admission_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL REFERENCES uploaded_documents(id) ON DELETE CASCADE,
    order_number TEXT NOT NULL,
    order_date TEXT NOT NULL,
    education_level TEXT NOT NULL CHECK (education_level IN ('ординатура', 'аспирантура')),
    specialty_code TEXT NOT NULL,
    specialty_name TEXT NOT NULL,
    financing_type TEXT NOT NULL CHECK (financing_type IN ('бюджет', 'целевая квота', 'договор')),
    admission_stage TEXT NOT NULL CHECK (admission_stage IN ('основной', 'допконкурс')),
    enrolled_count INTEGER NOT NULL CHECK (enrolled_count >= 0),
    student_identifiers_json TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class PdfInput:
    """Represents a PDF file payload on disk or in memory."""

    filename: str
    raw_bytes: bytes


@dataclass(frozen=True)
class DiagnosticFailure:
    """Structured diagnostic emitted when a PDF cannot be parsed."""

    filename: str
    error_code: str
    message: str


@dataclass
class BatchIngestionResult:
    """Summary of a batch PDF ingestion run."""

    ingested_documents: int = 0
    ingested_records: int = 0
    skipped_duplicates: List[str] = field(default_factory=list)
    failures: List[DiagnosticFailure] = field(default_factory=list)


class AdmissionParseError(Exception):
    """Raised when a PDF is corrupted or does not match expected admission schemas."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


def init_admission_db(conn: sqlite3.Connection) -> None:
    """Initializes uploaded_documents and admission_records tables."""
    conn.executescript(SCHEMA_SQL)


def _detect_doc_type(filename: str) -> str:
    if filename.startswith("Svedeniya_o_zachislenii_"):
        return "enrollment_order"
    if filename.startswith("Svedeniya_o_prieme_"):
        return "admission_summary"
    raise AdmissionParseError(
        "UNRECOGNIZED_DOCUMENT_TYPE",
        f"Filename '{filename}' does not match Svedeniya_o_zachislenii_* or Svedeniya_o_prieme_*",
    )


def _extract_pdf_text(raw_bytes: bytes) -> str:
    if not raw_bytes.startswith(b"%PDF-"):
        raise AdmissionParseError("CORRUPTED_PDF", "Missing %PDF- header")
    match = re.search(rb"BT\s*(.*?)\s*ET", raw_bytes, flags=re.DOTALL)
    if not match:
        raise AdmissionParseError("CORRUPTED_PDF", "Missing PDF text block (BT ... ET)")
    try:
        text = match.group(1).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AdmissionParseError("CORRUPTED_PDF", f"Invalid UTF-8 text payload: {exc}") from exc
    if not text.strip():
        raise AdmissionParseError("EMPTY_PDF_TEXT", "Extracted PDF text is empty")
    return text


def _normalize_for_hash(raw_text: str) -> str:
    return re.sub(r"\s+", " ", raw_text).strip()


def _parse_admission_blocks(raw_text: str) -> List[dict]:
    order_match = re.search(
        r"Приказ\s+№\s*([^\s]+)\s+от\s+(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})",
        raw_text,
    )
    level_match = re.search(r"Уровень:\s*(ординатура|аспирантура)", raw_text)
    stage_match = re.search(r"Этап:\s*(основной|допконкурс)", raw_text)
    if not (order_match and level_match and stage_match):
        raise AdmissionParseError(
            "UNRECOGNIZED_CONTENT",
            "Missing required order header, education level, or admission stage",
        )

    order_number = order_match.group(1)
    order_date = order_match.group(2)
    education_level = level_match.group(1)
    admission_stage = stage_match.group(1)

    block_pattern = re.compile(
        r"Специальность:\s*([0-9.]+)\s+([^|\n]+?)\s*\|\s*"
        r"Финансирование:\s*(бюджет|целевая квота|договор)\s*\|\s*"
        r"Зачислено:\s*(\d+)\s*\|\s*"
        r"Идентификаторы:\s*([^\n]+)"
    )
    blocks = block_pattern.findall(raw_text)
    if not blocks:
        raise AdmissionParseError(
            "UNRECOGNIZED_CONTENT",
            "No structured specialty enrollment blocks found in document",
        )

    parsed_rows = []
    for specialty_code, specialty_name, financing_type, count_str, ids_raw in blocks:
        identifiers = [item.strip() for item in ids_raw.split(",") if item.strip()]
        declared_count = int(count_str)
        if declared_count != len(identifiers):
            raise AdmissionParseError(
                "COUNT_MISMATCH",
                f"Declared enrolled_count ({declared_count}) does not match identifier count ({len(identifiers)})",
            )
        parsed_rows.append(
            {
                "order_number": order_number,
                "order_date": order_date,
                "education_level": education_level,
                "specialty_code": specialty_code.strip(),
                "specialty_name": specialty_name.strip(),
                "financing_type": financing_type.strip(),
                "admission_stage": admission_stage,
                "enrolled_count": declared_count,
                "student_identifiers_json": json.dumps(identifiers, ensure_ascii=False),
            }
        )
    return parsed_rows


def ingest_pdf_batch(
    conn: sqlite3.Connection,
    pdfs: Iterable[PdfInput],
    now_fn: Optional[Callable[[], str]] = None,
) -> BatchIngestionResult:
    """Parses and ingests admission PDFs into SQLite with content-hash deduplication."""
    init_admission_db(conn)
    timestamp_fn = now_fn or (lambda: "2026-11-19T00:00:00Z")
    result = BatchIngestionResult()

    for pdf in pdfs:
        try:
            doc_type = _detect_doc_type(pdf.filename)
            raw_text = _extract_pdf_text(pdf.raw_bytes)
            content_hash = hashlib.sha256(_normalize_for_hash(raw_text).encode("utf-8")).hexdigest()

            existing = conn.execute(
                "SELECT id FROM uploaded_documents WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()
            if existing is not None:
                result.skipped_duplicates.append(pdf.filename)
                continue

            parsed_rows = _parse_admission_blocks(raw_text)

            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO uploaded_documents (filename, uploaded_at, raw_text, doc_type, content_hash)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (pdf.filename, timestamp_fn(), raw_text, doc_type, content_hash),
                )
                doc_id = cursor.lastrowid
                for row in parsed_rows:
                    conn.execute(
                        """
                        INSERT INTO admission_records (
                            doc_id,
                            order_number,
                            order_date,
                            education_level,
                            specialty_code,
                            specialty_name,
                            financing_type,
                            admission_stage,
                            enrolled_count,
                            student_identifiers_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            doc_id,
                            row["order_number"],
                            row["order_date"],
                            row["education_level"],
                            row["specialty_code"],
                            row["specialty_name"],
                            row["financing_type"],
                            row["admission_stage"],
                            row["enrolled_count"],
                            row["student_identifiers_json"],
                        ),
                    )
            result.ingested_documents += 1
            result.ingested_records += len(parsed_rows)
        except AdmissionParseError as exc:
            result.failures.append(
                DiagnosticFailure(
                    filename=pdf.filename,
                    error_code=exc.error_code,
                    message=exc.message,
                )
            )

    return result


def _make_pdf_bytes(body: str) -> bytes:
    return b"%PDF-1.4\n1 0 obj\nBT\n" + body.encode("utf-8") + b"\nET\n%%EOF"


def _build_eleven_pdf_corpus() -> List[PdfInput]:
    # File [1] (index 0 in 1-based list) is duplicated by files [10] and [11].
    shared_doc_1_body = (
        "Приказ № 101-к от 2026-08-15\n"
        "Уровень: ординатура\n"
        "Этап: основной\n"
        "Специальность: 31.08.01 Акушерство и гинекология | Финансирование: бюджет | Зачислено: 2 | "
        "Идентификаторы: 100-000-001 01, 100-000-002 02"
    )
    specs = [
        ("Svedeniya_o_zachislenii_01.pdf", shared_doc_1_body),
        (
            "Svedeniya_o_zachislenii_02.pdf",
            "Приказ № 102-к от 2026-08-15\nУровень: ординатура\nЭтап: основной\n"
            "Специальность: 31.08.49 Терапия | Финансирование: целевая квота | Зачислено: 3 | "
            "Идентификаторы: 200-000-001 11, 200-000-002 12, 200-000-003 13",
        ),
        (
            "Svedeniya_o_zachislenii_03.pdf",
            "Приказ № 103-к от 2026-08-16\nУровень: ординатура\nЭтап: основной\n"
            "Специальность: 31.08.67 Хирургия | Финансирование: договор | Зачислено: 2 | "
            "Идентификаторы: 300-000-001 21, 300-000-002 22",
        ),
        (
            "Svedeniya_o_zachislenii_04.pdf",
            "Приказ № 104-к от 2026-08-17\nУровень: аспирантура\nЭтап: основной\n"
            "Специальность: 3.1.18 Внутренние болезни | Финансирование: бюджет | Зачислено: 1 | "
            "Идентификаторы: 400-000-001 31",
        ),
        (
            "Svedeniya_o_zachislenii_05.pdf",
            "Приказ № 105-к от 2026-08-18\nУровень: ординатура\nЭтап: допконкурс\n"
            "Специальность: 31.08.02 Анестезиология-реаниматология | Финансирование: бюджет | Зачислено: 2 | "
            "Идентификаторы: 500-000-001 41, 500-000-002 42",
        ),
        (
            "Svedeniya_o_prieme_06.pdf",
            "Приказ № 106-к от 2026-08-19\nУровень: ординатура\nЭтап: основной\n"
            "Специальность: 31.08.42 Неврология | Финансирование: договор | Зачислено: 2 | "
            "Идентификаторы: 600-000-001 51, 600-000-002 52",
        ),
        (
            "Svedeniya_o_prieme_07.pdf",
            "Приказ № 107-к от 2026-08-20\nУровень: аспирантура\nЭтап: допконкурс\n"
            "Специальность: 3.1.20 Кардиология | Финансирование: целевая квота | Зачислено: 1 | "
            "Идентификаторы: 700-000-001 61",
        ),
        (
            "Svedeniya_o_prieme_08.pdf",
            "Приказ № 108-к от 2026-08-21\nУровень: ординатура\nЭтап: основной\n"
            "Специальность: 31.08.19 Педиатрия | Финансирование: бюджет | Зачислено: 2 | "
            "Идентификаторы: 800-000-001 71, 800-000-002 72",
        ),
        (
            "Svedeniya_o_prieme_09.pdf",
            "Приказ № 109-к от 2026-08-22\nУровень: аспирантура\nЭтап: основной\n"
            "Специальность: 3.1.9 Хирургия | Финансирование: договор | Зачислено: 1 | "
            "Идентификаторы: 900-000-001 81",
        ),
        ("Svedeniya_o_zachislenii_10_dup1.pdf", shared_doc_1_body + " "),
        ("Svedeniya_o_prieme_11_dup1.pdf", "  " + shared_doc_1_body),
    ]
    return [PdfInput(filename=name, raw_bytes=_make_pdf_bytes(body)) for name, body in specs]


@pytest.fixture
def db_conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "crie_admission.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_batch_processes_11_pdfs_and_deduplicates_1_10_11(db_conn: sqlite3.Connection) -> None:
    corpus = _build_eleven_pdf_corpus()
    assert len(corpus) == 11

    result = ingest_pdf_batch(db_conn, corpus, now_fn=lambda: "2026-11-19T00:00:00Z")

    assert result.failures == []
    assert result.ingested_documents == 9
    assert result.ingested_records == 9
    assert result.skipped_duplicates == [
        "Svedeniya_o_zachislenii_10_dup1.pdf",
        "Svedeniya_o_prieme_11_dup1.pdf",
    ]

    doc_count = db_conn.execute("SELECT COUNT(*) FROM uploaded_documents").fetchone()[0]
    rec_count = db_conn.execute("SELECT COUNT(*) FROM admission_records").fetchone()[0]
    assert doc_count == 9
    assert rec_count == 9

    row = db_conn.execute(
        "SELECT * FROM admission_records WHERE order_number = ?", ("101-к",)
    ).fetchone()
    assert row is not None
    assert row["order_date"] == "2026-08-15"
    assert row["education_level"] == "ординатура"
    assert row["specialty_code"] == "31.08.01"
    assert row["specialty_name"] == "Акушерство и гинекология"
    assert row["financing_type"] == "бюджет"
    assert row["admission_stage"] == "основной"
    assert row["enrolled_count"] == 2
    assert json.loads(row["student_identifiers_json"]) == ["100-000-001 01", "100-000-002 02"]


def test_corrupted_or_unrecognized_pdf_records_diagnostic_without_partial_commit(
    db_conn: sqlite3.Connection,
) -> None:
    valid_pdf = _build_eleven_pdf_corpus()[0]
    corrupted_pdf = PdfInput(filename="Svedeniya_o_zachislenii_broken.pdf", raw_bytes=b"NOT_A_PDF\x00\xff")
    unrecognized_pdf = PdfInput(
        filename="Svedeniya_o_prieme_invalid_schema.pdf",
        raw_bytes=_make_pdf_bytes("Произвольный текст без приказа и таблицы"),
    )
    unknown_name_pdf = PdfInput(
        filename="random_attachment.pdf",
        raw_bytes=_make_pdf_bytes("Приказ № 999-к от 2026-08-25"),
    )

    result = ingest_pdf_batch(
        db_conn,
        [valid_pdf, corrupted_pdf, unrecognized_pdf, unknown_name_pdf],
        now_fn=lambda: "2026-11-19T00:00:00Z",
    )

    assert result.ingested_documents == 1
    assert result.ingested_records == 1
    assert [(f.filename, f.error_code) for f in result.failures] == [
        ("Svedeniya_o_zachislenii_broken.pdf", "CORRUPTED_PDF"),
        ("Svedeniya_o_prieme_invalid_schema.pdf", "UNRECOGNIZED_CONTENT"),
        ("random_attachment.pdf", "UNRECOGNIZED_DOCUMENT_TYPE"),
    ]

    assert db_conn.execute("SELECT COUNT(*) FROM uploaded_documents").fetchone()[0] == 1
    assert db_conn.execute("SELECT COUNT(*) FROM admission_records").fetchone()[0] == 1


def test_reexecution_is_idempotent(db_conn: sqlite3.Connection) -> None:
    corpus = _build_eleven_pdf_corpus()
    first_run = ingest_pdf_batch(db_conn, corpus, now_fn=lambda: "2026-11-19T00:00:00Z")
    assert first_run.ingested_documents == 9
    assert first_run.ingested_records == 9

    second_run = ingest_pdf_batch(db_conn, corpus, now_fn=lambda: "2026-11-19T01:00:00Z")
    assert second_run.ingested_documents == 0
    assert second_run.ingested_records == 0
    assert len(second_run.skipped_duplicates) == 11
    assert second_run.failures == []

    assert db_conn.execute("SELECT COUNT(*) FROM uploaded_documents").fetchone()[0] == 9
    assert db_conn.execute("SELECT COUNT(*) FROM admission_records").fetchone()[0] == 9


def test_schema_constraints_reject_invalid_enums(db_conn: sqlite3.Connection) -> None:
    init_admission_db(db_conn)
    db_conn.execute(
        """
        INSERT INTO uploaded_documents (filename, uploaded_at, raw_text, doc_type, content_hash)
        VALUES ('Svedeniya_o_zachislenii_01.pdf', '2026-11-19T00:00:00Z', 'raw', 'enrollment_order', 'hash1')
        """
    )
    with pytest.raises(sqlite3.IntegrityError):
        db_conn.execute(
            """
            INSERT INTO admission_records (
                doc_id, order_number, order_date, education_level, specialty_code,
                specialty_name, financing_type, admission_stage, enrolled_count, student_identifiers_json
            ) VALUES (1, '101-к', '2026-08-15', 'бакалавриат', '31.08.01', 'Test', 'бюджет', 'основной', 1, '["1"]')
            """
        )
