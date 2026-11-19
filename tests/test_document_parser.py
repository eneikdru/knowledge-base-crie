"""Focused tests for the admission PDF SQLite schema and ingestion invariants."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

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
);

CREATE TABLE IF NOT EXISTS ingestion_diagnostics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class SyntheticPdfPayload:
    """Deterministic PDF fixture representing one admission/enrollment document."""

    index: int
    filename: str
    doc_type: str
    raw_text: str
    order_number: str
    order_date: str
    education_level: str
    specialty_code: str
    specialty_name: str
    financing_type: str
    admission_stage: str
    student_identifiers: tuple[str, ...]
    corrupted: bool = False


def _normalize_hash(raw_text: str) -> str:
    """Return a deterministic SHA-256 digest of normalized document text."""
    normalized = " ".join(raw_text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize an isolated SQLite database with the admission schema."""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    return conn


def _ingest_batch(
    conn: sqlite3.Connection,
    documents: list[SyntheticPdfPayload],
    fixed_timestamp: str = "2026-11-19T00:00:00Z",
) -> dict[str, int]:
    """Ingest documents transactionally with content deduplication and diagnostic logging."""
    stats = {"inserted": 0, "skipped_duplicates": 0, "failed": 0}
    for doc in documents:
        if doc.corrupted or not doc.raw_text.strip():
            with conn:
                conn.execute(
                    """
                    INSERT INTO ingestion_diagnostics (filename, status, error_message, recorded_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (doc.filename, "failed", "Corrupted or unrecognized PDF payload", fixed_timestamp),
                )
            stats["failed"] += 1
            continue

        digest = _normalize_hash(doc.raw_text)
        existing = conn.execute(
            "SELECT id FROM uploaded_documents WHERE content_hash = ?",
            (digest,),
        ).fetchone()
        if existing is not None:
            stats["skipped_duplicates"] += 1
            continue

        with conn:
            cursor = conn.execute(
                """
                INSERT INTO uploaded_documents (filename, uploaded_at, raw_text, doc_type, content_hash)
                VALUES (?, ?, ?, ?, ?)
                """,
                (doc.filename, fixed_timestamp, doc.raw_text, doc.doc_type, digest),
            )
            doc_id = cursor.lastrowid
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
                    doc.order_number,
                    doc.order_date,
                    doc.education_level,
                    doc.specialty_code,
                    doc.specialty_name,
                    doc.financing_type,
                    doc.admission_stage,
                    len(doc.student_identifiers),
                    json.dumps(list(doc.student_identifiers), ensure_ascii=False),
                ),
            )
        stats["inserted"] += 1
    return stats


def _build_eleven_pdf_batch() -> list[SyntheticPdfPayload]:
    """Build 11 deterministic fixtures where [1], [10], and [11] share duplicate content."""
    shared_duplicate_text = (
        "Приказ № 101-О от 2026-08-20 о зачислении в ординатуру "
        "31.08.01 Акушерство и гинекология бюджет основной этап: ID-001, ID-002"
    )
    specs = [
        (1, "Svedeniya_o_zachislenii_01.pdf", "zachislenie", shared_duplicate_text, "101-О", "2026-08-20", "ординатура", "31.08.01", "Акушерство и гинекология", "бюджет", "основной", ("ID-001", "ID-002")),
        (2, "Svedeniya_o_zachislenii_02.pdf", "zachislenie", "Unique doc 02", "102-О", "2026-08-21", "ординатура", "31.08.49", "Терапия", "целевая квота", "основной", ("ID-003",)),
        (3, "Svedeniya_o_zachislenii_03.pdf", "zachislenie", "Unique doc 03", "103-О", "2026-08-22", "ординатура", "31.08.67", "Хирургия", "договор", "основной", ("ID-004", "ID-005", "ID-006")),
        (4, "Svedeniya_o_zachislenii_04.pdf", "zachislenie", "Unique doc 04", "104-О", "2026-08-23", "аспирантура", "3.1.18", "Внутренние болезни", "бюджет", "основной", ("ID-007",)),
        (5, "Svedeniya_o_zachislenii_05.pdf", "zachislenie", "Unique doc 05", "105-О", "2026-08-24", "ординатура", "31.08.19", "Педиатрия", "целевая квота", "допконкурс", ("ID-008", "ID-009")),
        (6, "Svedeniya_o_prieme_06.pdf", "priem", "Unique doc 06", "201-П", "2026-08-25", "ординатура", "31.08.02", "Анестезиология", "бюджет", "основной", ("ID-010",)),
        (7, "Svedeniya_o_prieme_07.pdf", "priem", "Unique doc 07", "202-П", "2026-08-26", "аспирантура", "3.1.9", "Хирургия", "договор", "допконкурс", ("ID-011", "ID-012")),
        (8, "Svedeniya_o_prieme_08.pdf", "priem", "Unique doc 08", "203-П", "2026-08-27", "ординатура", "31.08.42", "Неврология", "бюджет", "основной", ("ID-013",)),
        (9, "Svedeniya_o_prieme_09.pdf", "priem", "Unique doc 09", "204-П", "2026-08-28", "аспирантура", "3.1.21", "Педиатрия", "целевая квота", "основной", ("ID-014",)),
        (10, "Svedeniya_o_zachislenii_10_copy.pdf", "zachislenie", shared_duplicate_text, "101-О", "2026-08-20", "ординатура", "31.08.01", "Акушерство и гинекология", "бюджет", "основной", ("ID-001", "ID-002")),
        (11, "Svedeniya_o_zachislenii_11_dup.pdf", "zachislenie", "  " + shared_duplicate_text + "  ", "101-О", "2026-08-20", "ординатура", "31.08.01", "Акушерство и гинекология", "бюджет", "основной", ("ID-001", "ID-002")),
    ]
    return [SyntheticPdfPayload(*item) for item in specs]


def test_eleven_pdf_batch_deduplicates_files_1_10_11_and_is_idempotent(tmp_path: Path) -> None:
    """Verify unique document persistence, [1]/[10]/[11] deduplication, and idempotent re-runs."""
    db_path = tmp_path / "crie_admissions.sqlite3"
    conn = _init_db(db_path)
    try:
        batch = _build_eleven_pdf_batch()
        first_stats = _ingest_batch(conn, batch)

        assert first_stats == {"inserted": 9, "skipped_duplicates": 2, "failed": 0}
        doc_count = conn.execute("SELECT COUNT(*) FROM uploaded_documents").fetchone()[0]
        rec_count = conn.execute("SELECT COUNT(*) FROM admission_records").fetchone()[0]
        assert doc_count == 9
        assert rec_count == 9

        filenames = {
            row[0]
            for row in conn.execute("SELECT filename FROM uploaded_documents").fetchall()
        }
        assert "Svedeniya_o_zachislenii_01.pdf" in filenames
        assert "Svedeniya_o_zachislenii_10_copy.pdf" not in filenames
        assert "Svedeniya_o_zachislenii_11_dup.pdf" not in filenames

        row = conn.execute(
            """
            SELECT order_number, education_level, specialty_code, financing_type,
                   admission_stage, enrolled_count, student_identifiers_json
            FROM admission_records
            WHERE specialty_code = '31.08.67'
            """
        ).fetchone()
        assert row is not None
        assert row[:6] == ("103-О", "ординатура", "31.08.67", "договор", "основной", 3)
        assert json.loads(row[6]) == ["ID-004", "ID-005", "ID-006"]

        second_stats = _ingest_batch(conn, batch)
        assert second_stats == {"inserted": 0, "skipped_duplicates": 11, "failed": 0}
        assert conn.execute("SELECT COUNT(*) FROM uploaded_documents").fetchone()[0] == 9
        assert conn.execute("SELECT COUNT(*) FROM admission_records").fetchone()[0] == 9
    finally:
        conn.close()


def test_corrupted_pdf_records_diagnostic_without_partial_rows(tmp_path: Path) -> None:
    """Verify corrupted PDFs log a diagnostic entry without committing partial admission rows."""
    db_path = tmp_path / "crie_admissions_corrupt.sqlite3"
    conn = _init_db(db_path)
    try:
        corrupted_doc = SyntheticPdfPayload(
            index=99,
            filename="Svedeniya_o_zachislenii_corrupt.pdf",
            doc_type="zachislenie",
            raw_text="",
            order_number="999-О",
            order_date="2026-08-30",
            education_level="ординатура",
            specialty_code="31.08.01",
            specialty_name="Акушерство и гинекология",
            financing_type="бюджет",
            admission_stage="основной",
            student_identifiers=(),
            corrupted=True,
        )
        valid_doc = _build_eleven_pdf_batch()[1]

        stats = _ingest_batch(conn, [corrupted_doc, valid_doc])
        assert stats == {"inserted": 1, "skipped_duplicates": 0, "failed": 1}
        assert conn.execute("SELECT COUNT(*) FROM uploaded_documents").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM admission_records").fetchone()[0] == 1

        diag = conn.execute(
            "SELECT filename, status, error_message FROM ingestion_diagnostics"
        ).fetchone()
        assert diag == (
            "Svedeniya_o_zachislenii_corrupt.pdf",
            "failed",
            "Corrupted or unrecognized PDF payload",
        )
    finally:
        conn.close()


def test_crie_document_parser_module_integration(tmp_path: Path) -> None:
    """Exercise crie_document_parser when present in the codebase."""
    parser = pytest.importorskip("crie_document_parser")
    assert hasattr(parser, "ensure_tables") or hasattr(parser, "parse_and_store")
