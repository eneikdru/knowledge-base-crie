"""Tests for the enrolled_trainees SQLite schema and deterministic PDF row extraction."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
JAVA_ENTITY_PATH = REPO_ROOT / "src" / "main" / "java" / "com" / "eneik" / "crie" / "models" / "persistence" / "InternalEntity.java"
FIXED_UPDATED_AT = "2026-11-24T10:45:36Z"

ENROLLED_TRAINEES_SCHEMA = """
CREATE TABLE IF NOT EXISTS enrolled_trainees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    snils_or_code TEXT NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('ординатура', 'аспирантура')),
    specialty TEXT NOT NULL,
    financing_type TEXT NOT NULL CHECK (financing_type IN ('бюджет', 'целевая квота', 'договор', 'допконкурс')),
    score REAL,
    order_doc_id TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (snils_or_code, specialty, order_doc_id)
);
"""

SPECIALTY_CODE_RE = re.compile(r"(\d{2}\.\d{2}\.\d{2})")
SNILS_OR_CODE_RE = re.compile(r"(\d{3}-\d{3}-\d{3}\s\d{2}|[A-Za-zА-Яа-я0-9_-]{4,})")
NUMBERED_ROW_PREFIX_RE = re.compile(r"^\s*\d+[.)]\s+")


@dataclass(frozen=True)
class EnrolledTraineeRecord:
    full_name: str
    snils_or_code: str
    level: str
    specialty: str
    financing_type: str
    score: Optional[float]
    order_doc_id: str
    updated_at: str


@dataclass(frozen=True)
class ExtractionOutcome:
    records: list[EnrolledTraineeRecord]
    diagnostics: list[dict[str, str]]


def normalize_level(raw: str) -> str:
    text = " ".join(raw.strip().lower().split())
    if "ординатур" in text:
        return "ординатура"
    if "аспирантур" in text:
        return "аспирантура"
    raise ValueError(f"Unsupported education level: {raw!r}")


def normalize_financing_type(raw: str) -> str:
    text = " ".join(raw.strip().lower().split())
    if any(token in text for token in ("допконкурс", "доп. конкурс", "доп конкурс", "дополнительн")):
        return "допконкурс"
    if "целев" in text:
        return "целевая квота"
    if any(token in text for token in ("договор", "платн", "внебюджет", "коммерч")):
        return "договор"
    if any(token in text for token in ("бюджет", "кцп", "общ")):
        return "бюджет"
    raise ValueError(f"Unsupported financing type: {raw!r}")


def normalize_specialty(raw: str) -> str:
    cleaned = " ".join(raw.strip().split())
    match = SPECIALTY_CODE_RE.search(cleaned)
    return match.group(1) if match else cleaned


def _split_row_cells(line: str) -> list[str]:
    if "|" in line:
        return [cell.strip() for cell in line.strip("| ").split("|") if cell.strip()]
    if "\t" in line:
        return [cell.strip() for cell in line.split("\t") if cell.strip()]
    if ";" in line:
        return [cell.strip() for cell in line.split(";") if cell.strip()]
    return [cell.strip() for cell in re.split(r"\s{2,}", line.strip()) if cell.strip()]


def extract_enrollment_rows(
    document_pages: Iterable[str],
    order_doc_id: str,
    filename: str,
    updated_at: str = FIXED_UPDATED_AT,
    logger: Optional[logging.Logger] = None,
) -> ExtractionOutcome:
    """Deterministically extracts trainee rows from table cells and numbered lists."""
    log = logger or logging.getLogger("crie_document_parser")
    records: list[EnrolledTraineeRecord] = []
    diagnostics: list[dict[str, str]] = []
    current_level = "ординатура"
    current_specialty = ""
    current_financing = "бюджет"

    for page_index, page_text in enumerate(document_pages, start=1):
        if not isinstance(page_text, str) or "\x00" in page_text:
            diag = {
                "filename": filename,
                "order_doc_id": order_doc_id,
                "page": str(page_index),
                "error_type": "corrupted_page_stream",
                "detail": "Non-text or null-byte PDF page content skipped",
            }
            diagnostics.append(diag)
            log.error("Malformed PDF page %s", json.dumps(diag, ensure_ascii=False))
            continue

        for line_number, raw_line in enumerate(page_text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue

            lower_line = line.lower()
            if "аспирантур" in lower_line and len(_split_row_cells(line)) <= 2:
                current_level = "аспирантура"
            elif "ординатур" in lower_line and len(_split_row_cells(line)) <= 2:
                current_level = "ординатура"

            spec_match = SPECIALTY_CODE_RE.search(line)
            if spec_match and len(_split_row_cells(line)) <= 2:
                current_specialty = spec_match.group(1)
                continue

            if len(_split_row_cells(line)) <= 2:
                try:
                    current_financing = normalize_financing_type(line)
                    continue
                except ValueError:
                    pass

            normalized_line = NUMBERED_ROW_PREFIX_RE.sub("", line)
            cells = _split_row_cells(normalized_line)
            if len(cells) < 5:
                continue

            # Skip table headers
            if any(header in cells[0].lower() for header in ("фио", "ф.и.о", "№", "список")):
                continue

            try:
                # Strip leading row index cell if present in table layout
                if cells[0].rstrip(".)").isdigit():
                    cells = cells[1:]
                if len(cells) < 5:
                    raise ValueError(f"Expected at least 5 data columns, got {len(cells)}")

                full_name = " ".join(cells[0].split())
                snils_match = SNILS_OR_CODE_RE.search(cells[1])
                if not snils_match:
                    raise ValueError(f"Invalid SNILS or code: {cells[1]!r}")
                snils_or_code = " ".join(snils_match.group(1).split())

                if len(cells) >= 6:
                    level = normalize_level(cells[2])
                    specialty = normalize_specialty(cells[3])
                    financing_type = normalize_financing_type(cells[4])
                    score_raw = cells[5]
                else:
                    level = current_level
                    specialty = normalize_specialty(cells[2]) or current_specialty
                    financing_type = normalize_financing_type(cells[3]) if cells[3] else current_financing
                    score_raw = cells[4]

                score = float(score_raw.replace(",", ".")) if score_raw not in ("-", "", "н/д") else None
                records.append(
                    EnrolledTraineeRecord(
                        full_name=full_name,
                        snils_or_code=snils_or_code,
                        level=level,
                        specialty=specialty,
                        financing_type=financing_type,
                        score=score,
                        order_doc_id=order_doc_id,
                        updated_at=updated_at,
                    )
                )
            except ValueError as exc:
                diag = {
                    "filename": filename,
                    "order_doc_id": order_doc_id,
                    "page": str(page_index),
                    "line": str(line_number),
                    "error_type": "malformed_row",
                    "detail": str(exc),
                }
                diagnostics.append(diag)
                log.error("Failed to parse enrollment row %s", json.dumps(diag, ensure_ascii=False))

    return ExtractionOutcome(records=records, diagnostics=diagnostics)


def upsert_enrolled_trainees(conn: sqlite3.Connection, records: Iterable[EnrolledTraineeRecord]) -> int:
    count = 0
    with conn:
        for rec in records:
            conn.execute(
                """
                INSERT INTO enrolled_trainees (
                    full_name, snils_or_code, level, specialty, financing_type, score, order_doc_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(snils_or_code, specialty, order_doc_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    level = excluded.level,
                    financing_type = excluded.financing_type,
                    score = excluded.score,
                    updated_at = excluded.updated_at
                """,
                (
                    rec.full_name,
                    rec.snils_or_code,
                    rec.level,
                    rec.specialty,
                    rec.financing_type,
                    rec.score,
                    rec.order_doc_id,
                    rec.updated_at,
                ),
            )
            count += 1
    return count


def test_java_internal_entity_matches_enrolled_trainees_schema() -> None:
    source = JAVA_ENTITY_PATH.read_text(encoding="utf-8")
    for column in (
        "id",
        "full_name",
        "snils_or_code",
        "level",
        "specialty",
        "financing_type",
        "score",
        "order_doc_id",
        "updated_at",
    ):
        assert column in source
    for enum_value in ("ординатура", "аспирантура", "бюджет", "целевая квота", "договор", "допконкурс"):
        assert enum_value in source


def test_deterministic_extraction_and_sqlite_persistence(tmp_path: Path) -> None:
    doc_1_pages = [
        """
        Сведения о зачислении (ординатура)
        № | ФИО | СНИЛС / Код | Уровень | Специальность | Основание приема | Балл
        1 | Иванов Иван Иванович | 112-233-445 95 | ординатура | 31.08.19 Фтизиатрия | бюджет | 214.5
        2 | Петрова Анна Сергеевна | 223-344-556 01 | клиническая ординатура | 31.08.35 Инфекционные болезни | целевое обучение | 208,0
        """
    ]
    doc_2_pages = [
        """
        Сведения о приеме (аспирантура)
        1) Сидоров Алексей Петрович ; ASP-2026-007 ; аспирантура ; 32.08.12 Эпидемиология ; по договору об оказании платных услуг ; 189.0
        2) Кузнецова Мария Олеговна ; ASP-2026-011 ; аспирантура ; 32.08.12 Эпидемиология ; дополнительный конкурс ; 195.5
        """
    ]

    outcome_1 = extract_enrollment_rows(doc_1_pages, order_doc_id="pdf-id-1", filename="Svedeniya_o_zachislenii_1.pdf")
    outcome_2 = extract_enrollment_rows(doc_2_pages, order_doc_id="pdf-id-2", filename="Svedeniya_o_prieme_2.pdf")

    assert outcome_1.diagnostics == []
    assert outcome_2.diagnostics == []

    db_path = tmp_path / "crie_enrolled.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(ENROLLED_TRAINEES_SCHEMA)
        inserted = upsert_enrolled_trainees(conn, outcome_1.records + outcome_2.records)
        # Re-running ingestion is idempotent
        upsert_enrolled_trainees(conn, outcome_1.records + outcome_2.records)
        assert inserted == 4

        rows = conn.execute(
            """
            SELECT full_name, snils_or_code, level, specialty, financing_type, score, order_doc_id
            FROM enrolled_trainees
            ORDER BY financing_type, full_name
            """
        ).fetchall()
    finally:
        conn.close()

    assert len(rows) == 4
    by_financing = {row[4]: row for row in rows}
    assert set(by_financing.keys()) == {"бюджет", "целевая квота", "договор", "допконкурс"}

    assert by_financing["бюджет"][2] == "ординатура"
    assert by_financing["бюджет"][3] == "31.08.19"
    assert by_financing["бюджет"][5] == pytest.approx(214.5)
    assert by_financing["бюджет"][6] == "pdf-id-1"

    assert by_financing["целевая квота"][3] == "31.08.35"
    assert by_financing["целевая квота"][5] == pytest.approx(208.0)
    assert by_financing["целевая квота"][6] == "pdf-id-1"

    assert by_financing["договор"][2] == "аспирантура"
    assert by_financing["договор"][3] == "32.08.12"
    assert by_financing["договор"][6] == "pdf-id-2"

    assert by_financing["допконкурс"][2] == "аспирантура"
    assert by_financing["допконкурс"][5] == pytest.approx(195.5)
    assert by_financing["допконкурс"][6] == "pdf-id-2"


def test_corrupted_pdf_preserves_valid_rows_and_logs_diagnostics(caplog: pytest.LogCaptureFixture) -> None:
    malformed_pages = [
        "\x00\x01CORRUPTED_STREAM",
        """
        1 | Смирнов Дмитрий Львович | 334-455-667 12 | ординатура | 31.08.19 | бюджет | 201.0
        2 | Битая Запись | ??? | ординатура | 31.08.19 | неизвестно | 150.0
        """,
    ]
    with caplog.at_level(logging.ERROR):
        outcome = extract_enrollment_rows(
            malformed_pages,
            order_doc_id="pdf-id-11",
            filename="Svedeniya_o_zachislenii_11_corrupted.pdf",
        )

    assert len(outcome.records) == 1
    assert outcome.records[0].full_name == "Смирнов Дмитрий Львович"
    assert outcome.records[0].order_doc_id == "pdf-id-11"
    assert len(outcome.diagnostics) == 2
    assert all(d["filename"] == "Svedeniya_o_zachislenii_11_corrupted.pdf" for d in outcome.diagnostics)
    assert "Svedeniya_o_zachislenii_11_corrupted.pdf" in caplog.text
