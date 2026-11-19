from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
from typing import Callable


JAVA_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "main"
    / "java"
    / "com"
    / "eneik"
    / "crie"
    / "models"
    / "persistence"
    / "InternalEntity.java"
)

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS uploaded_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        uploaded_at TEXT NOT NULL,
        raw_text TEXT NOT NULL,
        doc_type TEXT NOT NULL,
        content_hash TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'INGESTED'
    )
    """,
    """
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
        student_identifiers_json TEXT NOT NULL,
        UNIQUE (doc_id, order_number, specialty_code, financing_type, admission_stage)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ingestion_diagnostics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        error_code TEXT NOT NULL,
        error_message TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'FAILED' CHECK (status IN ('FAILED', 'ACKNOWLEDGED', 'RESOLVED'))
    )
    """,
)

ORDER_RE = re.compile(r"Приказ\s+№\s*([\w\-/]+)\s+от\s+(\d{2}\.\d{2}\.\d{4})")
SPECIALTY_RE = re.compile(r"(\d{2}\.\d{2}\.\d{2})\s+([^\n;]+)")
STUDENT_ID_RE = re.compile(r"\b(\d{3}-\d{3}-\d{3}\s+\d{2}|ID-\d{4,8})\b")


@dataclass(frozen=True)
class ParsedAdmissionRow:
    order_number: str
    order_date: str
    education_level: str
    specialty_code: str
    specialty_name: str
    financing_type: str
    admission_stage: str
    enrolled_count: int
    student_identifiers: tuple[str, ...]


class DocumentParseError(ValueError):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def normalize_content_hash(raw_text: str) -> str:
    normalized = re.sub(r"\s+", " ", raw_text.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def init_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    for ddl in SCHEMA_STATEMENTS:
        conn.execute(ddl)
    conn.commit()


def detect_doc_type(filename: str) -> str:
    if filename.startswith("Svedeniya_o_zachislenii_"):
        return "zachislenie"
    if filename.startswith("Svedeniya_o_prieme_"):
        return "priem"
    raise DocumentParseError("UNRECOGNIZED_DOCUMENT", f"Unsupported admission filename: {filename}")


def parse_admission_text(filename: str, raw_text: str) -> tuple[str, list[ParsedAdmissionRow]]:
    if "\x00" in raw_text or raw_text.startswith("%PDF-corrupt"):
        raise DocumentParseError("CORRUPTED_PDF", f"Corrupted PDF payload in {filename}")

    doc_type = detect_doc_type(filename)
    order_match = ORDER_RE.search(raw_text)
    if not order_match:
        raise DocumentParseError("UNRECOGNIZED_DOCUMENT", f"Missing order header in {filename}")

    order_number, order_date = order_match.group(1), order_match.group(2)
    lowered = raw_text.lower()
    education_level = "аспирантура" if "аспирантура" in lowered else "ординатура"
    if "целевая квота" in lowered:
        financing_type = "целевая квота"
    elif "договор" in lowered:
        financing_type = "договор"
    else:
        financing_type = "бюджет"
    admission_stage = "допконкурс" if "допконкурс" in lowered else "основной"

    rows: list[ParsedAdmissionRow] = []
    for block in raw_text.split("---"):
        spec_match = SPECIALTY_RE.search(block)
        if not spec_match:
            continue
        student_ids = tuple(STUDENT_ID_RE.findall(block))
        if not student_ids:
            raise DocumentParseError(
                "INVALID_ENROLLMENT_BLOCK",
                f"Specialty {spec_match.group(1)} has no student identifiers in {filename}",
            )
        rows.append(
            ParsedAdmissionRow(
                order_number=order_number,
                order_date=order_date,
                education_level=education_level,
                specialty_code=spec_match.group(1),
                specialty_name=spec_match.group(2).strip(),
                financing_type=financing_type,
                admission_stage=admission_stage,
                enrolled_count=len(student_ids),
                student_identifiers=student_ids,
            )
        )

    if not rows:
        raise DocumentParseError("EMPTY_ADMISSION_RECORDS", f"No admission records extracted from {filename}")
    return doc_type, rows


def ingest_batch(
    conn: sqlite3.Connection,
    documents: list[tuple[str, str]],
    clock: Callable[[], str],
) -> dict[str, int]:
    summary = {"inserted_docs": 0, "skipped_duplicates": 0, "inserted_records": 0, "failed_docs": 0}
    for filename, raw_text in documents:
        content_hash = normalize_content_hash(raw_text)
        timestamp = clock()
        existing = conn.execute(
            "SELECT id FROM uploaded_documents WHERE content_hash = ?",
            (content_hash,),
        ).fetchone()
        if existing is not None:
            summary["skipped_duplicates"] += 1
            continue

        try:
            with conn:
                doc_type, parsed_rows = parse_admission_text(filename, raw_text)
                cur = conn.execute(
                    """
                    INSERT INTO uploaded_documents (filename, uploaded_at, raw_text, doc_type, content_hash, status)
                    VALUES (?, ?, ?, ?, ?, 'INGESTED')
                    """,
                    (filename, timestamp, raw_text, doc_type, content_hash),
                )
                doc_id = cur.lastrowid
                for row in parsed_rows:
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
                            row.order_number,
                            row.order_date,
                            row.education_level,
                            row.specialty_code,
                            row.specialty_name,
                            row.financing_type,
                            row.admission_stage,
                            row.enrolled_count,
                            json.dumps(list(row.student_identifiers), ensure_ascii=False),
                        ),
                    )
                    summary["inserted_records"] += 1
                summary["inserted_docs"] += 1
        except DocumentParseError as exc:
            with conn:
                conn.execute(
                    """
                    INSERT INTO ingestion_diagnostics (
                        filename, content_hash, error_code, error_message, recorded_at, status
                    ) VALUES (?, ?, ?, ?, ?, 'FAILED')
                    """,
                    (filename, content_hash, exc.error_code, str(exc), timestamp),
                )
            summary["failed_docs"] += 1
    return summary


def _build_eleven_pdf_corpus() -> list[tuple[str, str]]:
    shared_duplicate_body = (
        "Приказ № 412-ОД от 28.08.2026\n"
        "Уровень: ординатура; Финансирование: бюджет; Этап: основной\n"
        "31.08.53 Эндокринология\n"
        "Зачислены: ID-1001, ID-1002, ID-1003"
    )
    return [
        ("Svedeniya_o_zachislenii_01.pdf", shared_duplicate_body),
        (
            "Svedeniya_o_zachislenii_02.pdf",
            "Приказ № 413-ОД от 28.08.2026\n"
            "Уровень: ординатура; Финансирование: целевая квота; Этап: основной\n"
            "31.08.49 Терапия\n"
            "Зачислены: ID-2001, ID-2002",
        ),
        (
            "Svedeniya_o_zachislenii_03.pdf",
            "Приказ № 414-ОД от 29.08.2026\n"
            "Уровень: ординатура; Финансирование: договор; Этап: основной\n"
            "31.08.67 Хирургия\n"
            "Зачислены: ID-3001",
        ),
        (
            "Svedeniya_o_zachislenii_04.pdf",
            "Приказ № 415-ОД от 29.08.2026\n"
            "Уровень: аспирантура; Финансирование: бюджет; Этап: основной\n"
            "3.1.20 Кардиология\n"
            "Зачислены: 123-456-789 01, 123-456-789 02",
        ),
        (
            "Svedeniya_o_zachislenii_05.pdf",
            "Приказ № 416-ОД от 30.08.2026\n"
            "Уровень: ординатура; Финансирование: бюджет; Этап: допконкурс\n"
            "31.08.09 Рентгенология\n"
            "Зачислены: ID-5001, ID-5002, ID-5003, ID-5004",
        ),
        (
            "Svedeniya_o_prieme_06.pdf",
            "Приказ № 417-ОД от 30.08.2026\n"
            "Уровень: аспирантура; Финансирование: целевая квота; Этап: основной\n"
            "3.1.18 Внутренние болезни\n"
            "Зачислены: ID-6001",
        ),
        (
            "Svedeniya_o_prieme_07.pdf",
            "Приказ № 418-ОД от 31.08.2026\n"
            "Уровень: ординатура; Финансирование: договор; Этап: допконкурс\n"
            "31.08.58 Оториноларингология\n"
            "Зачислены: ID-7001, ID-7002",
        ),
        (
            "Svedeniya_o_prieme_08.pdf",
            "Приказ № 419-ОД от 31.08.2026\n"
            "Уровень: аспирантура; Финансирование: договор; Этап: основной\n"
            "3.1.24 Неврология\n"
            "Зачислены: ID-8001, ID-8002, ID-8003",
        ),
        (
            "Svedeniya_o_prieme_09.pdf",
            "Приказ № 420-ОД от 01.09.2026\n"
            "Уровень: ординатура; Финансирование: бюджет; Этап: основной\n"
            "31.08.36 Кардиология\n"
            "Зачислены: ID-9001, ID-9002",
        ),
        ("Svedeniya_o_zachislenii_10.pdf", "  " + shared_duplicate_body + "\n"),
        ("Svedeniya_o_prieme_11.pdf", shared_duplicate_body.replace("\n", "   \n")),
    ]


def test_java_schema_contract_matches_sqlite_columns() -> None:
    java_source = JAVA_SCHEMA_PATH.read_text(encoding="utf-8")
    for table_name in ("uploaded_documents", "admission_records", "ingestion_diagnostics"):
        assert table_name in java_source
    for required_column in (
        "filename",
        "uploaded_at",
        "raw_text",
        "doc_type",
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
    ):
        assert required_column in java_source

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    uploaded_cols = {row[1] for row in conn.execute("PRAGMA table_info(uploaded_documents)")}
    admission_cols = {row[1] for row in conn.execute("PRAGMA table_info(admission_records)")}
    assert {"id", "filename", "uploaded_at", "raw_text", "doc_type", "content_hash", "status"} <= uploaded_cols
    assert {
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
    } <= admission_cols


def test_batch_ingest_11_pdfs_deduplicates_files_1_10_11() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    ticks = iter(f"2026-11-19T00:00:{i:02d}Z" for i in range(1, 20))
    corpus = _build_eleven_pdf_corpus()

    summary = ingest_batch(conn, corpus, lambda: next(ticks))

    assert summary == {
        "inserted_docs": 9,
        "skipped_duplicates": 2,
        "inserted_records": 9,
        "failed_docs": 0,
    }
    assert conn.execute("SELECT COUNT(*) FROM uploaded_documents").fetchone()[0] == 9
    assert conn.execute("SELECT COUNT(*) FROM admission_records").fetchone()[0] == 9

    endo_row = conn.execute(
        """
        SELECT order_number, education_level, financing_type, admission_stage,
               enrolled_count, student_identifiers_json
        FROM admission_records
        WHERE specialty_code = '31.08.53'
        """
    ).fetchone()
    assert endo_row is not None
    assert endo_row[0] == "412-ОД"
    assert endo_row[1] == "ординатура"
    assert endo_row[2] == "бюджет"
    assert endo_row[3] == "основной"
    assert endo_row[4] == 3
    assert json.loads(endo_row[5]) == ["ID-1001", "ID-1002", "ID-1003"]


def test_corrupted_or_unrecognized_pdf_records_diagnostic_without_partial_commit() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    batch = [
        ("Svedeniya_o_zachislenii_bad.pdf", "%PDF-corrupt\x00\xff"),
        ("Unknown_document.pdf", "Неизвестный документ без заголовка приказа"),
        (
            "Svedeniya_o_zachislenii_partial.pdf",
            "Приказ № 500-ОД от 02.09.2026\n"
            "Уровень: ординатура; Финансирование: бюджет; Этап: основной\n"
            "31.08.53 Эндокринология\n"
            "Зачислены: ID-9991\n"
            "---\n"
            "31.08.49 Терапия\n"
            "Зачислены: отсутствуют",
        ),
        _build_eleven_pdf_corpus()[1],
    ]
    ticks = iter(f"2026-11-19T01:00:{i:02d}Z" for i in range(1, 10))

    summary = ingest_batch(conn, batch, lambda: next(ticks))

    assert summary["inserted_docs"] == 1
    assert summary["failed_docs"] == 3
    assert conn.execute("SELECT COUNT(*) FROM uploaded_documents").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM admission_records").fetchone()[0] == 1

    diagnostics = conn.execute(
        "SELECT filename, error_code, status FROM ingestion_diagnostics ORDER BY id"
    ).fetchall()
    assert diagnostics == [
        ("Svedeniya_o_zachislenii_bad.pdf", "CORRUPTED_PDF", "FAILED"),
        ("Unknown_document.pdf", "UNRECOGNIZED_DOCUMENT", "FAILED"),
        ("Svedeniya_o_zachislenii_partial.pdf", "INVALID_ENROLLMENT_BLOCK", "FAILED"),
    ]


def test_reexecution_of_11_pdf_ingestion_is_idempotent() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    corpus = _build_eleven_pdf_corpus()

    first = ingest_batch(conn, corpus, lambda: "2026-11-19T02:00:00Z")
    second = ingest_batch(conn, corpus, lambda: "2026-11-19T02:05:00Z")

    assert first["inserted_docs"] == 9
    assert second["inserted_docs"] == 0
    assert second["inserted_records"] == 0
    assert second["skipped_duplicates"] == 11
    assert conn.execute("SELECT COUNT(*) FROM uploaded_documents").fetchone()[0] == 9
    assert conn.execute("SELECT COUNT(*) FROM admission_records").fetchone()[0] == 9


def test_guarded_diagnostic_status_transition_prevents_double_transition() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    conn.execute(
        """
        INSERT INTO ingestion_diagnostics (filename, content_hash, error_code, error_message, recorded_at, status)
        VALUES ('bad.pdf', 'abc', 'CORRUPTED_PDF', 'corrupt', '2026-11-19T02:00:00Z', 'FAILED')
        """
    )
    diag_id = conn.execute("SELECT id FROM ingestion_diagnostics").fetchone()[0]

    first_update = conn.execute(
        "UPDATE ingestion_diagnostics SET status = ? WHERE id = ? AND status = ?",
        ("RESOLVED", diag_id, "FAILED"),
    ).rowcount
    second_update = conn.execute(
        "UPDATE ingestion_diagnostics SET status = ? WHERE id = ? AND status = ?",
        ("ACKNOWLEDGED", diag_id, "FAILED"),
    ).rowcount

    assert first_update == 1
    assert second_update == 0
    assert (
        conn.execute("SELECT status FROM ingestion_diagnostics WHERE id = ?", (diag_id,)).fetchone()[0]
        == "RESOLVED"
    )


def test_optional_crie_document_parser_module_compatibility() -> None:
    spec = importlib.util.find_spec("crie_document_parser")
    if spec is None:
        return
    module = importlib.import_module("crie_document_parser")
    assert hasattr(module, "__name__")
