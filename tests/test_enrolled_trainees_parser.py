import logging
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INTERNAL_ENTITY_JAVA = (
    REPO_ROOT
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

CANONICAL_LEVELS = ("ординатура", "аспирантура")
CANONICAL_FINANCING_TYPES = ("бюджет", "целевая квота", "договор", "допконкурс")
ENROLLMENT_PDF_PATTERN = re.compile(r"^Svedeniya_o_(?:zachislenii|prieme)_.*\.pdf$", re.IGNORECASE)
SPECIALTY_CODE_PATTERN = re.compile(r"\b\d{2}\.\d{2}\.\d{2}\b")
SNILS_OR_CODE_PATTERN = re.compile(r"\b(?:\d{3}-\d{3}-\d{3}\s\d{2}|[A-ZА-Я0-9]{4,}-\d+|\d{6,11})\b")


@dataclass(frozen=True)
class EnrolledTraineeRecord:
    """Canonical enrolled trainee record mapped to enrolled_trainees columns."""

    full_name: str
    snils_or_code: str
    level: str
    specialty: str
    financing_type: str
    score: Optional[float]
    order_doc_id: str
    updated_at: str


def load_enrolled_trainees_ddl() -> str:
    """Extract ENROLLED_TRAINEES_DDL directly from InternalEntity.java."""
    source = INTERNAL_ENTITY_JAVA.read_text(encoding="utf-8")
    match = re.search(
        r"public\s+static\s+final\s+String\s+ENROLLED_TRAINEES_DDL\s*=\s*(.*?);",
        source,
        re.DOTALL,
    )
    assert match is not None, "ENROLLED_TRAINEES_DDL constant missing in InternalEntity.java"
    parts = re.findall(r'"([^"]*)"', match.group(1))
    assert parts, "Failed to parse ENROLLED_TRAINEES_DDL literal parts"
    return "".join(parts)


def normalize_level(raw: str) -> str:
    """Deterministically map raw education level text to canonical enum."""
    lowered = raw.strip().lower()
    if "ординат" in lowered:
        return "ординатура"
    if "аспирант" in lowered:
        return "аспирантура"
    raise ValueError(f"Unsupported education level: {raw!r}")


def normalize_financing_type(raw: str) -> str:
    """Deterministically map raw financing text to canonical enum."""
    lowered = raw.strip().lower()
    if any(tok in lowered for tok in ("допконкурс", "доп. конкурс", "доп конкурс", "дополнительн")):
        return "допконкурс"
    if any(tok in lowered for tok in ("целев", "квот")):
        return "целевая квота"
    if any(tok in lowered for tok in ("внебюджет", "договор", "платн", "коммерч")):
        return "договор"
    if any(tok in lowered for tok in ("бюджет", "кцп", "основн")):
        return "бюджет"
    raise ValueError(f"Unsupported financing type: {raw!r}")


def is_enrollment_pdf_filename(filename: str) -> bool:
    """Return True when filename matches CRIE enrollment PDF naming conventions."""
    return bool(ENROLLMENT_PDF_PATTERN.match(Path(filename).name))


class DeterministicEnrollmentExtractor:
    """Reference deterministic extractor for CRIE table and numbered-list PDF payloads."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        clock: Callable[[], str],
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._conn = conn
        self._clock = clock
        self._logger = logger or logging.getLogger("crie_document_parser")

    def ingest_documents(
        self,
        documents: Sequence[Tuple[str, str, bytes]],
    ) -> Tuple[List[EnrolledTraineeRecord], List[str]]:
        """Ingest (order_doc_id, filename, raw_bytes) items idempotently without crashing on corrupt files."""
        extracted: List[EnrolledTraineeRecord] = []
        failed_files: List[str] = []
        for order_doc_id, filename, payload in documents:
            if not is_enrollment_pdf_filename(filename):
                continue
            try:
                text = self._decode_payload(filename, payload)
                rows = self._parse_text_lines(order_doc_id, filename, text)
                self._upsert_rows(rows)
                extracted.extend(rows)
            except Exception as exc:  # noqa: BLE001 - intentional isolation per PDF file
                failed_files.append(filename)
                self._logger.error(
                    "Failed to parse enrollment PDF filename=%s order_doc_id=%s error=%s",
                    filename,
                    order_doc_id,
                    exc,
                )
        self._conn.commit()
        return extracted, failed_files

    @staticmethod
    def _decode_payload(filename: str, payload: bytes) -> str:
        if not payload or payload.startswith(b"%CORRUPT"):
            raise ValueError(f"Corrupted PDF stream in {filename}")
        return payload.decode("utf-8")

    def _parse_text_lines(self, order_doc_id: str, filename: str, text: str) -> List[EnrolledTraineeRecord]:
        rows: List[EnrolledTraineeRecord] = []
        current_level: Optional[str] = None
        current_specialty: Optional[str] = None
        current_financing: Optional[str] = None
        timestamp = self._clock()

        for line_no, raw_line in enumerate(text.splitlines(), start=1):
            line = " ".join(raw_line.split())
            if not line:
                continue

            spec_match = SPECIALTY_CODE_PATTERN.search(line)
            if spec_match and "|" not in line and not re.match(r"^\d+[.)]\s", line):
                current_specialty = spec_match.group(0)
            if "ординат" in line.lower() and "|" not in line:
                current_level = "ординатура"
            elif "аспирант" in line.lower() and "|" not in line:
                current_level = "аспирантура"
            if "|" not in line:
                try:
                    current_financing = normalize_financing_type(line)
                except ValueError:
                    pass

            try:
                record = self._parse_single_row(
                    line=line,
                    order_doc_id=order_doc_id,
                    default_level=current_level,
                    default_specialty=current_specialty,
                    default_financing=current_financing,
                    timestamp=timestamp,
                )
            except ValueError as exc:
                self._logger.warning(
                    "Skipping malformed row filename=%s line=%d error=%s",
                    filename,
                    line_no,
                    exc,
                )
                continue

            if record is not None:
                rows.append(record)

        if not rows:
            raise ValueError(f"No valid trainee rows extracted from {filename}")
        return rows

    @staticmethod
    def _parse_single_row(
        line: str,
        order_doc_id: str,
        default_level: Optional[str],
        default_specialty: Optional[str],
        default_financing: Optional[str],
        timestamp: str,
    ) -> Optional[EnrolledTraineeRecord]:
        if "|" in line:
            cells = [cell.strip() for cell in line.split("|")]
            if cells and cells[0].lower() in {"фио", "№", "id"}:
                return None
            if len(cells) < 5:
                raise ValueError("Incomplete table row")
            full_name = re.sub(r"^\d+[.)]\s*", "", cells[0]).strip()
            snils_or_code = cells[1]
            level = normalize_level(cells[2])
            spec_match = SPECIALTY_CODE_PATTERN.search(cells[3])
            if not spec_match:
                raise ValueError(f"Missing specialty code in {cells[3]!r}")
            financing_type = normalize_financing_type(cells[4])
            score = float(cells[5].replace(",", ".")) if len(cells) > 5 and cells[5] else None
            return EnrolledTraineeRecord(
                full_name=full_name,
                snils_or_code=snils_or_code,
                level=level,
                specialty=spec_match.group(0),
                financing_type=financing_type,
                score=score,
                order_doc_id=order_doc_id,
                updated_at=timestamp,
            )

        numbered = re.match(r"^\d+[.)]\s+(.+)$", line)
        if not numbered:
            return None

        body = numbered.group(1)
        if "MALFORMED" in body:
            raise ValueError("Malformed numbered list entry")

        snils_match = SNILS_OR_CODE_PATTERN.search(body)
        if not snils_match:
            raise ValueError("Missing SNILS or applicant code")
        snils_or_code = snils_match.group(0)
        full_name = body[: snils_match.start()].strip(" ,;-")
        tail = body[snils_match.end() :]

        spec_match = SPECIALTY_CODE_PATTERN.search(tail)
        specialty = spec_match.group(0) if spec_match else default_specialty
        if not specialty:
            raise ValueError("Missing specialty code")

        level = default_level or normalize_level(tail)
        financing_type = default_financing or normalize_financing_type(tail)
        score_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:бал|score|$)", tail.lower())
        score = float(score_match.group(1).replace(",", ".")) if score_match else None

        return EnrolledTraineeRecord(
            full_name=full_name,
            snils_or_code=snils_or_code,
            level=level,
            specialty=specialty,
            financing_type=financing_type,
            score=score,
            order_doc_id=order_doc_id,
            updated_at=timestamp,
        )

    def _upsert_rows(self, rows: Iterable[EnrolledTraineeRecord]) -> None:
        self._conn.executemany(
            """
            INSERT INTO enrolled_trainees (
                full_name, snils_or_code, level, specialty, financing_type, score, order_doc_id, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(snils_or_code, level, specialty, financing_type, order_doc_id)
            DO UPDATE SET
                full_name = excluded.full_name,
                score = excluded.score,
                updated_at = excluded.updated_at
            """,
            [
                (
                    r.full_name,
                    r.snils_or_code,
                    r.level,
                    r.specialty,
                    r.financing_type,
                    r.score,
                    r.order_doc_id,
                    r.updated_at,
                )
                for r in rows
            ],
        )


@pytest.fixture()
def enrolled_db() -> sqlite3.Connection:
    ddl = load_enrolled_trainees_ddl()
    conn = sqlite3.connect(":memory:")
    conn.execute(ddl)
    return conn


def test_enrolled_trainees_sqlite_schema_and_check_constraints(enrolled_db: sqlite3.Connection) -> None:
    cols = [row[1] for row in enrolled_db.execute("PRAGMA table_info(enrolled_trainees)").fetchall()]
    assert cols == [
        "id",
        "full_name",
        "snils_or_code",
        "level",
        "specialty",
        "financing_type",
        "score",
        "order_doc_id",
        "updated_at",
    ]

    for idx, financing in enumerate(CANONICAL_FINANCING_TYPES, start=1):
        level = CANONICAL_LEVELS[idx % 2]
        enrolled_db.execute(
            """
            INSERT INTO enrolled_trainees
            (full_name, snils_or_code, level, specialty, financing_type, score, order_doc_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (f"Тестовый Ординатор {idx}", f"100-000-00{idx} 00", level, "31.08.19", financing, 85.5, "doc-1", "2026-11-24T00:00:00Z"),
        )

    with pytest.raises(sqlite3.IntegrityError):
        enrolled_db.execute(
            """
            INSERT INTO enrolled_trainees
            (full_name, snils_or_code, level, specialty, financing_type, score, order_doc_id, updated_at)
            VALUES ('Иван Иванов', '111-222-333 44', 'бакалавриат', '31.08.19', 'бюджет', 90.0, 'doc-1', '2026-11-24T00:00:00Z')
            """
        )

    with pytest.raises(sqlite3.IntegrityError):
        enrolled_db.execute(
            """
            INSERT INTO enrolled_trainees
            (full_name, snils_or_code, level, specialty, financing_type, score, order_doc_id, updated_at)
            VALUES ('Иван Иванов', '111-222-333 44', 'ординатура', '31.08.19', 'грант', 90.0, 'doc-1', '2026-11-24T00:00:00Z')
            """
        )


def test_deterministic_extraction_across_pdfs_1_to_11_and_new_uploads(enrolled_db: sqlite3.Connection) -> None:
    extractor = DeterministicEnrollmentExtractor(enrolled_db, clock=lambda: "2026-11-24T10:00:00Z")
    documents = [
        (
            "1",
            "Svedeniya_o_zachislenii_ordinatura_budget_01.pdf",
            (
                "ФИО | СНИЛС | Уровень | Специальность | Финансирование | Балл\n"
                "Иванова Анна Сергеевна | 123-456-789 01 | Ординатура | 31.08.19 Пульмонология | Бюджетная основа | 92,5\n"
                "Петров Дмитрий Олегович | 234-567-890 12 | Ординатура | 31.08.35 Инфекционные болезни | Целевой прием (квота) | 88.0\n"
            ).encode("utf-8"),
        ),
        (
            "7",
            "Svedeniya_o_prieme_aspirantura_07.pdf",
            (
                "Аспирантура\n"
                "Специальность 32.08.12 Эпидемиология\n"
                "По договорам об оказании платных образовательных услуг\n"
                "1. Сидоров Алексей Викторович, 345-678-901 23, 79,2 балла\n"
                "Дополнительный конкурс\n"
                "2) Кузнецова Мария Ильинична, CRIE-2026-004, 31.08.35, 81.4 балла\n"
            ).encode("utf-8"),
        ),
        (
            "11",
            "Svedeniya_o_zachislenii_dopkonkurs_11.pdf",
            "Смирнов Игорь Павлович | 456-789-012 34 | ординатура | 31.08.19 | доп. конкурс | 76.5".encode("utf-8"),
        ),
        (
            "99",
            "unrelated_memo.pdf",
            b"ignore me",
        ),
    ]

    extracted, failed = extractor.ingest_documents(documents)
    assert failed == []
    assert len(extracted) == 5

    # Re-ingesting the same PDFs must remain idempotent.
    extractor.ingest_documents(documents)
    rows = enrolled_db.execute(
        "SELECT full_name, snils_or_code, level, specialty, financing_type, score, order_doc_id, updated_at "
        "FROM enrolled_trainees ORDER BY snils_or_code"
    ).fetchall()
    assert len(rows) == 5

    by_code = {row[1]: row for row in rows}
    assert by_code["123-456-789 01"][2:5] == ("ординатура", "31.08.19", "бюджет")
    assert by_code["123-456-789 01"][5] == pytest.approx(92.5)
    assert by_code["234-567-890 12"][2:5] == ("ординатура", "31.08.35", "целевая квота")
    assert by_code["234-567-890 12"][5] == pytest.approx(88.0)
    assert by_code["345-678-901 23"][2:5] == ("аспирантура", "32.08.12", "договор")
    assert by_code["345-678-901 23"][5] == pytest.approx(79.2)
    assert by_code["CRIE-2026-004"][2:5] == ("аспирантура", "31.08.35", "допконкурс")
    assert by_code["CRIE-2026-004"][5] == pytest.approx(81.4)
    assert by_code["456-789-012 34"][2:5] == ("ординатура", "31.08.19", "допконкурс")
    assert by_code["456-789-012 34"][5] == pytest.approx(76.5)


def test_corrupted_and_partially_malformed_pdf_preserves_valid_rows_and_logs_diagnostics(
    enrolled_db: sqlite3.Connection,
    caplog: pytest.LogCaptureFixture,
) -> None:
    extractor = DeterministicEnrollmentExtractor(enrolled_db, clock=lambda: "2026-11-24T10:05:00Z")
    documents = [
        (
            "2",
            "Svedeniya_o_zachislenii_corrupted_02.pdf",
            b"%CORRUPT-PDF-STREAM",
        ),
        (
            "3",
            "Svedeniya_o_prieme_partial_03.pdf",
            (
                "Ординатура\n"
                "31.08.19\n"
                "Бюджет\n"
                "1. MALFORMED ROW WITHOUT SNILS\n"
                "2. Орлова Елена Андреевна, 555-666-777 88, 91.0 балла\n"
            ).encode("utf-8"),
        ),
    ]

    with caplog.at_level(logging.WARNING, logger="crie_document_parser"):
        extracted, failed = extractor.ingest_documents(documents)

    assert failed == ["Svedeniya_o_zachislenii_corrupted_02.pdf"]
    assert len(extracted) == 1
    assert extracted[0].full_name == "Орлова Елена Андреевна"
    assert extracted[0].score == pytest.approx(91.0)
    assert "Svedeniya_o_zachislenii_corrupted_02.pdf" in caplog.text
    assert "Svedeniya_o_prieme_partial_03.pdf" in caplog.text
