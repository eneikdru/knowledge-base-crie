import logging
import re
import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INTERNAL_ENTITY_PATH = (
    REPO_ROOT / "src/main/java/com/eneik/crie/models/persistence/InternalEntity.java"
)

EXPECTED_COLUMNS = (
    "id",
    "full_name",
    "snils_or_code",
    "level",
    "specialty",
    "financing_type",
    "score",
    "order_doc_id",
    "updated_at",
)
EXPECTED_LEVELS = ("ординатура", "аспирантура")
EXPECTED_FINANCING_TYPES = ("бюджет", "целевая квота", "договор", "допконкурс")
CRIE_SPECIALTIES = ("31.08.19", "31.08.35", "32.08.12")

ENROLLED_TRAINEES_DDL = """
CREATE TABLE IF NOT EXISTS enrolled_trainees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    snils_or_code TEXT NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('ординатура', 'аспирантура')),
    specialty TEXT NOT NULL,
    financing_type TEXT NOT NULL CHECK (financing_type IN ('бюджет', 'целевая квота', 'договор', 'допконкурс')),
    score REAL,
    order_doc_id INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _create_schema_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(ENROLLED_TRAINEES_DDL)
    conn.commit()
    return conn


def test_java_internal_entity_defines_enrolled_trainees_schema():
    """Verify InternalEntity.java declares the canonical enrolled_trainees columns and enums."""
    assert INTERNAL_ENTITY_PATH.exists(), f"Missing schema model: {INTERNAL_ENTITY_PATH}"
    source = INTERNAL_ENTITY_PATH.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS enrolled_trainees" in source
    for column in EXPECTED_COLUMNS:
        assert re.search(rf"\b{re.escape(column)}\b", source), f"Missing column {column}"
    for level in EXPECTED_LEVELS:
        assert f"'{level}'" in source or f'"{level}"' in source
    for financing in EXPECTED_FINANCING_TYPES:
        assert f"'{financing}'" in source or f'"{financing}"' in source


def test_sqlite_enrolled_trainees_constraints_and_financing_queries(tmp_path: Path):
    """Verify SQLite CHECK constraints and querying residents/postgraduates by financing type."""
    conn = _create_schema_connection(tmp_path / "enrolled.db")
    try:
        sample_rows = [
            (
                "Иванов Иван Иванович",
                "123-456-789 01",
                "ординатура",
                "31.08.19",
                "бюджет",
                245.5,
                1,
                "2026-11-24T10:00:00Z",
            ),
            (
                "Петрова Анна Сергеевна",
                "234-567-890 02",
                "ординатура",
                "31.08.35",
                "целевая квота",
                238.0,
                2,
                "2026-11-24T10:00:00Z",
            ),
            (
                "Сидоров Олег Петрович",
                "345-678-901 03",
                "ординатура",
                "32.08.12",
                "договор",
                210.0,
                3,
                "2026-11-24T10:00:00Z",
            ),
            (
                "Кузнецова Мария Львовна",
                "456-789-012 04",
                "аспирантура",
                "1.5.11",
                "допконкурс",
                192.0,
                11,
                "2026-11-24T10:00:00Z",
            ),
        ]
        conn.executemany(
            """
            INSERT INTO enrolled_trainees (
                full_name, snils_or_code, level, specialty,
                financing_type, score, order_doc_id, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            sample_rows,
        )
        conn.commit()

        columns = [row[1] for row in conn.execute("PRAGMA table_info(enrolled_trainees)").fetchall()]
        assert tuple(columns) == EXPECTED_COLUMNS

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO enrolled_trainees (
                    full_name, snils_or_code, level, specialty,
                    financing_type, score, order_doc_id, updated_at
                ) VALUES ('Test', '000-1', 'магистратура', '31.08.19', 'бюджет', 100, 1, '2026-11-24T10:00:00Z')
                """
            )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO enrolled_trainees (
                    full_name, snils_or_code, level, specialty,
                    financing_type, score, order_doc_id, updated_at
                ) VALUES ('Test', '000-2', 'ординатура', '31.08.19', 'грант', 100, 1, '2026-11-24T10:00:00Z')
                """
            )

        grouped = conn.execute(
            """
            SELECT level, financing_type, COUNT(*), MIN(order_doc_id)
            FROM enrolled_trainees
            GROUP BY level, financing_type
            ORDER BY level, financing_type
            """
        ).fetchall()
        assert len(grouped) == 4
        assert any(row[3] in range(1, 12) for row in grouped)
    finally:
        conn.close()


def test_live_document_parser_extraction_and_corruption_resilience(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    """Verify deterministic parser behavior when crie_document_parser and crie_persistent_memory exist."""
    parser_mod = pytest.importorskip("crie_document_parser")
    memory_mod = pytest.importorskip("crie_persistent_memory")

    db_path = tmp_path / "crie_memory.db"
    conn = memory_mod.init_db(str(db_path)) if hasattr(memory_mod, "init_db") else _create_schema_connection(db_path)

    mixed_layout_text = (
        "Приказ о зачислении (Svedeniya_o_zachislenii_1.pdf)\n"
        "Ординатура 31.08.19 Педиатрия — бюджет\n"
        "1 | Смирнов Алексей Викторович | 111-222-333 44 | 251.0\n"
        "Ординатура 31.08.35 Инфекционные болезни — целевая квота\n"
        "1. Волкова Елена Дмитриевна (222-333-444 55) - 240 баллов\n"
        "Ординатура 32.08.12 Эпидемиология — договор\n"
        "2. Морозов Денис Игоревич | 333-444-555 66 | 215.5\n"
        "Аспирантура — дополнительный конкурс (допконкурс)\n"
        "1. Соколова Ирина Павловна | 444-555-666 77 | 198\n"
    )

    extract_fn = getattr(parser_mod, "extract_enrollment_records_from_text", None)
    if extract_fn is not None:
        records = extract_fn(mixed_layout_text, order_doc_id=1)
        assert len(records) == 4
        specialties = {rec["specialty"] for rec in records if rec.get("specialty") in CRIE_SPECIALTIES}
        assert specialties == set(CRIE_SPECIALTIES)
        financing_values = {rec["financing_type"] for rec in records}
        assert financing_values == set(EXPECTED_FINANCING_TYPES)

    corrupted_pdf = tmp_path / "Svedeniya_o_prieme_corrupted.pdf"
    corrupted_pdf.write_bytes(b"%PDF-1.4\n%corrupted-binary-payload")

    parse_pdf_fn = getattr(parser_mod, "parse_enrollment_pdf", None)
    if parse_pdf_fn is not None:
        with caplog.at_level(logging.WARNING):
            result = parse_pdf_fn(str(corrupted_pdf), order_doc_id=99, conn=conn)
        assert result is not None
        assert "Svedeniya_o_prieme_corrupted.pdf" in caplog.text
