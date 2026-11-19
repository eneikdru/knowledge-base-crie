"""Tests for persistent SQLite contingent schema, deduplication, and aggregation."""

import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

import pytest

try:
    import crie_persistent_memory  # type: ignore
except ImportError:  # crie_persistent_memory.py is delivered in a separate slice
    crie_persistent_memory = None


SCHEMA_SQL = """
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
    education_level TEXT NOT NULL,
    specialty_code TEXT NOT NULL,
    specialty_name TEXT NOT NULL,
    financing_type TEXT NOT NULL,
    admission_stage TEXT NOT NULL,
    enrolled_count INTEGER NOT NULL CHECK (enrolled_count >= 0),
    student_identifiers_json TEXT NOT NULL DEFAULT '[]',
    order_signature TEXT NOT NULL UNIQUE,
    FOREIGN KEY (doc_id) REFERENCES uploaded_documents(id) ON DELETE CASCADE,
    UNIQUE (
        order_number,
        order_date,
        education_level,
        specialty_code,
        financing_type,
        admission_stage
    )
);
"""


class ContingentMemoryContract:
    """Reference SQLite repository implementing the contingent storage contract."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    @staticmethod
    def compute_content_hash(raw_text: str) -> str:
        return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_order_signature(
        order_number: str,
        order_date: str,
        education_level: str,
        specialty_code: str,
        financing_type: str,
        admission_stage: str,
    ) -> str:
        canonical = "|".join(
            [
                order_number.strip(),
                order_date.strip(),
                education_level.strip(),
                specialty_code.strip(),
                financing_type.strip(),
                admission_stage.strip(),
            ]
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def upsert_document(
        self,
        filename: str,
        uploaded_at: str,
        raw_text: str,
        doc_type: str,
        content_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        doc_hash = content_hash or self.compute_content_hash(raw_text)
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM uploaded_documents WHERE content_hash = ?",
                (doc_hash,),
            ).fetchone()
            if existing is not None:
                return {"inserted": False, "deduplicated": True, "doc_id": int(existing["id"])}

            cur = conn.execute(
                """
                INSERT INTO uploaded_documents (filename, uploaded_at, raw_text, doc_type, content_hash)
                VALUES (?, ?, ?, ?, ?)
                """,
                (filename, uploaded_at, raw_text, doc_type, doc_hash),
            )
            return {"inserted": True, "deduplicated": False, "doc_id": int(cur.lastrowid)}

    def upsert_admission_record(
        self,
        doc_id: int,
        order_number: str,
        order_date: str,
        education_level: str,
        specialty_code: str,
        specialty_name: str,
        financing_type: str,
        admission_stage: str,
        enrolled_count: int,
        student_identifiers: List[str],
    ) -> Dict[str, Any]:
        signature = self.compute_order_signature(
            order_number=order_number,
            order_date=order_date,
            education_level=education_level,
            specialty_code=specialty_code,
            financing_type=financing_type,
            admission_stage=admission_stage,
        )
        students_json = json.dumps(student_identifiers, ensure_ascii=False)
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM admission_records WHERE order_signature = ?",
                (signature,),
            ).fetchone()
            if existing is not None:
                return {
                    "inserted": False,
                    "deduplicated": True,
                    "record_id": int(existing["id"]),
                }

            cur = conn.execute(
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
                    student_identifiers_json,
                    order_signature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    order_number,
                    order_date,
                    education_level,
                    specialty_code,
                    specialty_name,
                    financing_type,
                    admission_stage,
                    enrolled_count,
                    students_json,
                    signature,
                ),
            )
            return {
                "inserted": True,
                "deduplicated": False,
                "record_id": int(cur.lastrowid),
            }

    def aggregate_admissions(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    specialty_code,
                    specialty_name,
                    education_level,
                    financing_type,
                    admission_stage,
                    SUM(enrolled_count) AS total_enrolled,
                    GROUP_CONCAT(DISTINCT doc_id) AS doc_ids,
                    GROUP_CONCAT(DISTINCT order_number || ' (' || order_date || ')') AS order_refs
                FROM admission_records
                GROUP BY
                    specialty_code,
                    specialty_name,
                    education_level,
                    financing_type,
                    admission_stage
                ORDER BY
                    specialty_code ASC,
                    education_level ASC,
                    financing_type ASC,
                    admission_stage ASC
                """
            ).fetchall()
            return [dict(row) for row in rows]


def _make_store(db_path: Path) -> Any:
    if crie_persistent_memory is not None and hasattr(crie_persistent_memory, "ContingentMemoryStore"):
        return crie_persistent_memory.ContingentMemoryStore(db_path)
    return ContingentMemoryContract(db_path)


def test_schema_creates_tables_columns_fk_and_unique_constraints(tmp_path: Path) -> None:
    db_path = tmp_path / "contingent.db"
    store = _make_store(db_path)
    # Calling init_schema again on an existing DB path must remain idempotent.
    store.init_schema()

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "uploaded_documents" in tables
        assert "admission_records" in tables

        doc_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(uploaded_documents)").fetchall()
        }
        assert {
            "id",
            "filename",
            "uploaded_at",
            "raw_text",
            "doc_type",
            "content_hash",
        }.issubset(doc_cols)

        adm_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(admission_records)").fetchall()
        }
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
            "order_signature",
        }.issubset(adm_cols)

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO admission_records (
                    doc_id, order_number, order_date, education_level,
                    specialty_code, specialty_name, financing_type, admission_stage,
                    enrolled_count, student_identifiers_json, order_signature
                ) VALUES (9999, 'ORD-1', '2026-08-15', 'ординатура',
                    '31.08.01', 'Акушерство и гинекология', 'бюджет', 'основной',
                    2, '["ID-1","ID-2"]', 'sig-orphan')
                """
            )


def test_document_and_order_deduplication_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "contingent.db"
    store = _make_store(db_path)

    first_doc = store.upsert_document(
        filename="Svedeniya_o_zachislenii_1.pdf",
        uploaded_at="2026-11-19T00:00:00Z",
        raw_text="Приказ № 101 от 2026-08-15 по ординатуре 31.08.01",
        doc_type="enrollment_order",
    )
    duplicate_doc = store.upsert_document(
        filename="Svedeniya_o_zachislenii_1 [1].pdf",
        uploaded_at="2026-11-19T00:05:00Z",
        raw_text="Приказ № 101 от 2026-08-15 по ординатуре 31.08.01",
        doc_type="enrollment_order",
    )

    assert first_doc["inserted"] is True
    assert first_doc["deduplicated"] is False
    assert duplicate_doc["inserted"] is False
    assert duplicate_doc["deduplicated"] is True
    assert duplicate_doc["doc_id"] == first_doc["doc_id"]

    first_rec = store.upsert_admission_record(
        doc_id=first_doc["doc_id"],
        order_number="101",
        order_date="2026-08-15",
        education_level="ординатура",
        specialty_code="31.08.01",
        specialty_name="Акушерство и гинекология",
        financing_type="бюджет",
        admission_stage="основной",
        enrolled_count=3,
        student_identifiers=["A-01", "A-02", "A-03"],
    )
    duplicate_rec = store.upsert_admission_record(
        doc_id=first_doc["doc_id"],
        order_number="101",
        order_date="2026-08-15",
        education_level="ординатура",
        specialty_code="31.08.01",
        specialty_name="Акушерство и гинекология",
        financing_type="бюджет",
        admission_stage="основной",
        enrolled_count=3,
        student_identifiers=["A-01", "A-02", "A-03"],
    )

    assert first_rec["inserted"] is True
    assert first_rec["deduplicated"] is False
    assert duplicate_rec["inserted"] is False
    assert duplicate_rec["deduplicated"] is True
    assert duplicate_rec["record_id"] == first_rec["record_id"]

    totals = store.aggregate_admissions()
    assert len(totals) == 1
    assert totals[0]["total_enrolled"] == 3


def test_aggregation_query_returns_exact_grouped_totals_and_persists_across_sessions(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "contingent.db"
    writer = _make_store(db_path)

    doc1 = writer.upsert_document(
        filename="Svedeniya_o_zachislenii_main.pdf",
        uploaded_at="2026-11-19T01:00:00Z",
        raw_text="Main admission order payload",
        doc_type="enrollment_order",
    )
    doc2 = writer.upsert_document(
        filename="Svedeniya_o_zachislenii_extra.pdf",
        uploaded_at="2026-11-19T01:10:00Z",
        raw_text="Additional admission order payload",
        doc_type="enrollment_order",
    )

    writer.upsert_admission_record(
        doc_id=doc1["doc_id"],
        order_number="201",
        order_date="2026-08-10",
        education_level="ординатура",
        specialty_code="31.08.01",
        specialty_name="Акушерство и гинекология",
        financing_type="бюджет",
        admission_stage="основной",
        enrolled_count=4,
        student_identifiers=["S1", "S2", "S3", "S4"],
    )
    writer.upsert_admission_record(
        doc_id=doc2["doc_id"],
        order_number="205",
        order_date="2026-08-22",
        education_level="ординатура",
        specialty_code="31.08.01",
        specialty_name="Акушерство и гинекология",
        financing_type="бюджет",
        admission_stage="основной",
        enrolled_count=2,
        student_identifiers=["S5", "S6"],
    )
    writer.upsert_admission_record(
        doc_id=doc2["doc_id"],
        order_number="206",
        order_date="2026-08-25",
        education_level="аспирантура",
        specialty_code="3.1.4",
        specialty_name="Акушерство и гинекология",
        financing_type="договор",
        admission_stage="допконкурс",
        enrolled_count=1,
        student_identifiers=["P1"],
    )

    # Re-open a fresh store instance against the same SQLite path to verify persistence.
    reader = _make_store(db_path)
    grouped = reader.aggregate_admissions()

    assert len(grouped) == 2
    assert grouped[0]["specialty_code"] == "3.1.4"
    assert grouped[0]["education_level"] == "аспирантура"
    assert grouped[0]["financing_type"] == "договор"
    assert grouped[0]["admission_stage"] == "допконкурс"
    assert grouped[0]["total_enrolled"] == 1
    assert "206 (2026-08-25)" in grouped[0]["order_refs"]

    assert grouped[1]["specialty_code"] == "31.08.01"
    assert grouped[1]["education_level"] == "ординатура"
    assert grouped[1]["financing_type"] == "бюджет"
    assert grouped[1]["admission_stage"] == "основной"
    assert grouped[1]["total_enrolled"] == 6
    assert str(doc1["doc_id"]) in str(grouped[1]["doc_ids"])
    assert str(doc2["doc_id"]) in str(grouped[1]["doc_ids"])
    assert "201 (2026-08-10)" in grouped[1]["order_refs"]
    assert "205 (2026-08-22)" in grouped[1]["order_refs"]
