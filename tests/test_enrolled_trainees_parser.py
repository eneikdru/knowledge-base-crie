import logging
import re
import sqlite3
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import pytest

CANONICAL_LEVELS = ("ординатура", "аспирантура")
CANONICAL_FINANCING = ("бюджет", "целевая квота", "договор", "допконкурс")

SNILS_OR_CODE_RE = re.compile(r"\b(?:\d{3}-\d{3}-\d{3}\s\d{2}|[A-ZА-Я]{2,4}-\d{3,6}|\d{6,11})\b")
SPECIALTY_RE = re.compile(r"\b\d{2}\.\d{2}\.\d{2}\b")
NUMBERED_ROW_RE = re.compile(r"^\s*(\d+)[.)]\s+(.+)$")
PDF_PREFIX_RE = re.compile(r"^(Svedeniya_o_zachislenii_|Svedeniya_o_prieme_).*\.pdf$", re.IGNORECASE)


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
class ParseDiagnostic:
    filename: str
    order_doc_id: str
    line_number: int
    reason: str


@dataclass(frozen=True)
class ExtractionResult:
    records: List[EnrolledTraineeRecord]
    diagnostics: List[ParseDiagnostic]


def normalize_level(raw_text: str, specialty: str = "") -> str:
    lowered = (raw_text or "").strip().lower()
    if any(token in lowered for token in ("ординат", "орд.")):
        return "ординатура"
    if any(token in lowered for token in ("аспирант", "асп.")):
        return "аспирантура"
    if specialty.startswith(("31.08.", "32.08.")):
        return "ординатура"
    if specialty.startswith(("1.", "3.", "5.")):
        return "аспирантура"
    raise ValueError(f"Unrecognized education level: {raw_text!r}")


def normalize_financing(raw_text: str) -> str:
    lowered = (raw_text or "").strip().lower().replace("ё", "е")
    if any(token in lowered for token in ("допконкурс", "доп. конкурс", "дополнительн")):
        return "допконкурс"
    if any(token in lowered for token in ("целев", "квот")):
        return "целевая квота"
    if any(token in lowered for token in ("договор", "платн", "контракт", "внебюджет")):
        return "договор"
    if any(token in lowered for token in ("бюджет", "кцп", "основн")):
        return "бюджет"
    raise ValueError(f"Unrecognized financing type: {raw_text!r}")


def _parse_score(raw_score: str) -> Optional[float]:
    cleaned = raw_score.strip().replace(",", ".")
    if not cleaned or cleaned in {"-", "—", "н/д"}:
        return None
    match = re.search(r"\b\d{1,3}(?:\.\d{1,2})?\b", cleaned)
    if not match:
        raise ValueError(f"Invalid score value: {raw_score!r}")
    return float(match.group(0))


def init_enrolled_trainees_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS enrolled_trainees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            snils_or_code TEXT NOT NULL,
            level TEXT NOT NULL CHECK (level IN ('ординатура', 'аспирантура')),
            specialty TEXT NOT NULL,
            financing_type TEXT NOT NULL CHECK (
                financing_type IN ('бюджет', 'целевая квота', 'договор', 'допконкурс')
            ),
            score REAL,
            order_doc_id TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (snils_or_code, order_doc_id, specialty)
        )
        """
    )
    conn.commit()


def extract_trainees_from_text(
    text: str,
    filename: str,
    order_doc_id: str,
    now_fn: Callable[[], str],
    logger: Optional[logging.Logger] = None,
) -> ExtractionResult:
    active_logger = logger or logging.getLogger("crie_document_parser")
    records: List[EnrolledTraineeRecord] = []
    diagnostics: List[ParseDiagnostic] = []

    if not text or "\x00" in text or text.lstrip().startswith("%CORRUPT"):
        reason = "Malformed or unreadable PDF payload"
        diagnostics.append(
            ParseDiagnostic(
                filename=filename,
                order_doc_id=order_doc_id,
                line_number=0,
                reason=reason,
            )
        )
        active_logger.error("Failed to parse %s (%s): %s", filename, order_doc_id, reason)
        return ExtractionResult(records=records, diagnostics=diagnostics)

    timestamp = now_fn()
    default_level = ""
    default_specialty = ""
    default_financing = ""

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#") or line.lower().startswith(("уровень:", "специальность:", "финансирование:")):
            spec_match = SPECIALTY_RE.search(line)
            if spec_match:
                default_specialty = spec_match.group(0)
            try:
                default_level = normalize_level(line, default_specialty)
            except ValueError:
                pass
            try:
                default_financing = normalize_financing(line)
            except ValueError:
                pass
            continue

        try:
            if "|" in line:
                parts = [part.strip() for part in line.split("|") if part.strip()]
                if len(parts) < 5:
                    raise ValueError(f"Expected >= 5 table cells, got {len(parts)}")
                offset = 1 if parts[0].isdigit() else 0
                full_name = parts[offset]
                snils_or_code = parts[offset + 1]
                specialty_match = SPECIALTY_RE.search(parts[offset + 2])
                specialty = specialty_match.group(0) if specialty_match else parts[offset + 2]
                level = normalize_level(parts[offset + 2], specialty)
                financing = normalize_financing(parts[offset + 3])
                score = _parse_score(parts[offset + 4])
            else:
                numbered = NUMBERED_ROW_RE.match(line)
                if not numbered:
                    continue
                body = numbered.group(2)
                snils_match = SNILS_OR_CODE_RE.search(body)
                if not snils_match:
                    raise ValueError("Missing SNILS or applicant code in numbered list row")
                snils_or_code = snils_match.group(0)
                full_name = body[: snils_match.start()].strip(" ,;-")
                tail = body[snils_match.end() :].strip(" ,;-")
                spec_match = SPECIALTY_RE.search(tail)
                specialty = spec_match.group(0) if spec_match else default_specialty
                if not specialty:
                    raise ValueError("Missing specialty code in numbered list row")
                level = normalize_level(tail or default_level, specialty)
                financing = normalize_financing(tail or default_financing)
                score_match = re.search(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*(?:балл|$)", tail)
                score = _parse_score(score_match.group(1)) if score_match else None

            if not full_name:
                raise ValueError("Missing trainee full name")

            records.append(
                EnrolledTraineeRecord(
                    full_name=full_name,
                    snils_or_code=snils_or_code,
                    level=level,
                    specialty=specialty,
                    financing_type=financing,
                    score=score,
                    order_doc_id=order_doc_id,
                    updated_at=timestamp,
                )
            )
        except ValueError as exc:
            diagnostics.append(
                ParseDiagnostic(
                    filename=filename,
                    order_doc_id=order_doc_id,
                    line_number=line_no,
                    reason=str(exc),
                )
            )
            active_logger.warning(
                "Skipped malformed row in %s (%s) line %d: %s",
                filename,
                order_doc_id,
                line_no,
                exc,
            )

    return ExtractionResult(records=records, diagnostics=diagnostics)


def ingest_documents(
    conn: sqlite3.Connection,
    documents: Sequence[Tuple[str, str, str]],
    now_fn: Callable[[], str],
    logger: Optional[logging.Logger] = None,
) -> List[ParseDiagnostic]:
    init_enrolled_trainees_schema(conn)
    all_diagnostics: List[ParseDiagnostic] = []
    for doc_id, filename, text in documents:
        result = extract_trainees_from_text(
            text=text,
            filename=filename,
            order_doc_id=doc_id,
            now_fn=now_fn,
            logger=logger,
        )
        all_diagnostics.extend(result.diagnostics)
        if result.records:
            conn.execute("DELETE FROM enrolled_trainees WHERE order_doc_id = ?", (doc_id,))
            conn.executemany(
                """
                INSERT INTO enrolled_trainees (
                    full_name, snils_or_code, level, specialty,
                    financing_type, score, order_doc_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        rec.full_name,
                        rec.snils_or_code,
                        rec.level,
                        rec.specialty,
                        rec.financing_type,
                        rec.score,
                        rec.order_doc_id,
                        rec.updated_at,
                    )
                    for rec in result.records
                ],
            )
            conn.commit()
    return all_diagnostics


def query_enrolled_by_financing(
    conn: sqlite3.Connection,
    financing_type: Optional[str] = None,
    level: Optional[str] = None,
) -> List[Dict[str, object]]:
    sql = (
        "SELECT full_name, snils_or_code, level, specialty, financing_type, score, order_doc_id, updated_at "
        "FROM enrolled_trainees WHERE 1=1"
    )
    params: List[object] = []
    if financing_type is not None:
        sql += " AND financing_type = ?"
        params.append(financing_type)
    if level is not None:
        sql += " AND level = ?"
        params.append(level)
    sql += " ORDER BY order_doc_id, full_name"
    rows = conn.execute(sql, params).fetchall()
    return [
        {
            "full_name": row[0],
            "snils_or_code": row[1],
            "level": row[2],
            "specialty": row[3],
            "financing_type": row[4],
            "score": row[5],
            "order_doc_id": row[6],
            "updated_at": row[7],
        }
        for row in rows
    ]


def _fixed_now() -> str:
    return "2026-11-24T10:45:36Z"


def test_startup_extraction_for_pdf_ids_1_through_11() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        startup_docs = [
            (
                f"pdf-{idx}",
                (
                    f"Svedeniya_o_zachislenii_{idx}.pdf"
                    if idx <= 8
                    else f"Svedeniya_o_prieme_{idx}.pdf"
                ),
                (
                    f"1 | Кандидат {idx} | 100-200-30{idx:02d} 11 | 31.08.19 ординатура | "
                    f"{CANONICAL_FINANCING[(idx - 1) % 4]} | {80 + idx * 0.5}"
                ),
            )
            for idx in range(1, 12)
        ]
        for _, filename, _ in startup_docs:
            assert PDF_PREFIX_RE.match(filename)

        diagnostics = ingest_documents(conn, startup_docs, now_fn=_fixed_now)
        assert diagnostics == []

        rows = query_enrolled_by_financing(conn)
        assert len(rows) == 11
        assert {row["order_doc_id"] for row in rows} == {f"pdf-{i}" for i in range(1, 12)}
        assert all(row["updated_at"] == "2026-11-24T10:45:36Z" for row in rows)

        budget_rows = query_enrolled_by_financing(conn, financing_type="бюджет")
        assert len(budget_rows) == 3
        assert budget_rows[0]["score"] == pytest.approx(80.5)
    finally:
        conn.close()


def test_mixed_table_and_numbered_list_normalization_for_crie_specialties() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        doc_text = """
        # Приказ о зачислении в ординатуру и аспирантуру
        1 | Иванова Анна Сергеевна | 123-456-789 01 | 31.08.19 Ординатура | Бюджетная основа (КЦП) | 94.5
        2 | Петров Олег Игоревич | 234-567-890 12 | 31.08.35 Ординатор | Целевое обучение (квота) | 88,0
        3. Сидоров Павел Андреевич 345-678-901 23 32.08.12 по договорам об оказании платных услуг 76.25 балл
        4. Козлова Мария Викторовна ASP-2026-04 3.1.22 аспирантура дополнительный конкурс 91 балл
        """
        diagnostics = ingest_documents(
            conn,
            [("pdf-9", "Svedeniya_o_prieme_9.pdf", doc_text)],
            now_fn=_fixed_now,
        )
        assert diagnostics == []

        rows = query_enrolled_by_financing(conn)
        assert len(rows) == 4

        by_name = {row["full_name"]: row for row in rows}
        assert by_name["Иванова Анна Сергеевна"]["level"] == "ординатура"
        assert by_name["Иванова Анна Сергеевна"]["specialty"] == "31.08.19"
        assert by_name["Иванова Анна Сергеевна"]["financing_type"] == "бюджет"
        assert by_name["Иванова Анна Сергеевна"]["score"] == pytest.approx(94.5)

        assert by_name["Петров Олег Игоревич"]["specialty"] == "31.08.35"
        assert by_name["Петров Олег Игоревич"]["financing_type"] == "целевая квота"
        assert by_name["Петров Олег Игоревич"]["score"] == pytest.approx(88.0)

        assert by_name["Сидоров Павел Андреевич"]["level"] == "ординатура"
        assert by_name["Сидоров Павел Андреевич"]["specialty"] == "32.08.12"
        assert by_name["Сидоров Павел Андреевич"]["financing_type"] == "договор"
        assert by_name["Сидоров Павел Андреевич"]["score"] == pytest.approx(76.25)

        assert by_name["Козлова Мария Викторовна"]["level"] == "аспирантура"
        assert by_name["Козлова Мария Викторовна"]["financing_type"] == "допконкурс"
        assert by_name["Козлова Мария Викторовна"]["score"] == pytest.approx(91.0)
    finally:
        conn.close()


def test_corrupted_and_partially_malformed_pdf_preserves_valid_rows_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    conn = sqlite3.connect(":memory:")
    caplog.set_level(logging.WARNING, logger="crie_document_parser")
    try:
        partial_pdf = """
        1 | Смирнов Дмитрий Львович | 456-789-012 34 | 31.08.19 ординатура | бюджет | 89.0
        2 | битая строка без снилс
        3 | Волкова Елена Николаевна | 567-890-123 45 | 31.08.35 ординатура | договор | нечисло
        4 | Орлов Артем Сергеевич | 678-901-234 56 | 32.08.12 ординатура | допконкурс | 82.5
        """
        corrupted_pdf = "%CORRUPT-PDF-HEADER\x00\x01\x02"

        diagnostics = ingest_documents(
            conn,
            [
                ("pdf-10", "Svedeniya_o_zachislenii_partial.pdf", partial_pdf),
                ("pdf-11", "Svedeniya_o_prieme_corrupted.pdf", corrupted_pdf),
            ],
            now_fn=_fixed_now,
        )

        assert len(diagnostics) == 3
        assert any(d.filename == "Svedeniya_o_zachislenii_partial.pdf" and d.line_number == 2 for d in diagnostics)
        assert any(d.filename == "Svedeniya_o_zachislenii_partial.pdf" and d.line_number == 3 for d in diagnostics)
        assert any(d.filename == "Svedeniya_o_prieme_corrupted.pdf" and d.line_number == 0 for d in diagnostics)

        assert "Svedeniya_o_zachislenii_partial.pdf" in caplog.text
        assert "Svedeniya_o_prieme_corrupted.pdf" in caplog.text

        rows = query_enrolled_by_financing(conn)
        assert len(rows) == 2
        assert [row["full_name"] for row in rows] == [
            "Орлов Артем Сергеевич",
            "Смирнов Дмитрий Львович",
        ]
    finally:
        conn.close()
