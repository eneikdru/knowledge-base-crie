"""Focused SQLite schema, deduplication, and aggregation tests for contingent storage."""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

DDL_UPLOADED_DOCUMENTS = """
CREATE TABLE IF NOT EXISTS uploaded_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE
)
"""

DDL_ADMISSION_RECORDS = """
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
    student_identifiers_json TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (doc_id) REFERENCES uploaded_documents(id) ON DELETE CASCADE,
    UNIQUE (order_number, order_date, education_level, specialty_code, financing_type, admission_stage)
)
"""

AGGREGATION_SQL = """
SELECT
    specialty_code,
    specialty_name,
    education_level,
    financing_type,
    admission_stage,
    SUM(enrolled_count) AS total_enrolled,
    COUNT(*) AS record_count,
    GROUP_CONCAT(DISTINCT doc_id) AS doc_ids,
    GROUP_CONCAT(DISTINCT order_number || ' (' || order_date || ')') AS order_references
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


def _connect(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with foreign keys enabled and Row factory."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_schema(db_path: Path) -> None:
    """Initialize contingent tables on a fresh or existing SQLite database."""
    with _connect(db_path) as conn:
        conn.execute(DDL_UPLOADED_DOCUMENTS)
        conn.execute(DDL_ADMISSION_RECORDS)
        conn.commit()


def upsert_uploaded_document(
    db_path: Path,
    *,
    filename: str,
    uploaded_at: str,
    raw_text: str,
    doc_type: str,
    content_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a document idempotently by content_hash and return deduplication status."""
    resolved_hash = content_hash or hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    with _connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO uploaded_documents (filename, uploaded_at, raw_text, doc_type, content_hash)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(content_hash) DO NOTHING
            """,
            (filename, uploaded_at, raw_text, doc_type, resolved_hash),
        )
        if cur.rowcount == 1:
            conn.commit()
            return {
                "doc_id": cur.lastrowid,
                "inserted": True,
                "deduplicated": False,
                "content_hash": resolved_hash,
            }
        existing = conn.execute(
            "SELECT id FROM uploaded_documents WHERE content_hash = ?",
            (resolved_hash,),
        ).fetchone()
        return {
            "doc_id": existing["id"],
            "inserted": False,
            "deduplicated": True,
            "content_hash": resolved_hash,
        }


def insert_admission_record(
    db_path: Path,
    *,
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
    """Insert an admission record idempotently by composite order signature."""
    payload_json = json.dumps(student_identifiers, ensure_ascii=False)
    with _connect(db_path) as conn:
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
                student_identifiers_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(
                order_number,
                order_date,
                education_level,
                specialty_code,
                financing_type,
                admission_stage
            ) DO NOTHING
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
                payload_json,
            ),
        )
        if cur.rowcount == 1:
            conn.commit()
            return {"record_id": cur.lastrowid, "inserted": True, "deduplicated": False}
        existing = conn.execute(
            """
            SELECT id FROM admission_records
            WHERE order_number = ?
              AND order_date = ?
              AND education_level = ?
              AND specialty_code = ?
              AND financing_type = ?
              AND admission_stage = ?
            """,
            (
                order_number,
                order_date,
                education_level,
                specialty_code,
                financing_type,
                admission_stage,
            ),
        ).fetchone()
        return {"record_id": existing["id"], "inserted": False, "deduplicated": True}


def aggregate_admissions(db_path: Path) -> List[Dict[str, Any]]:
    """Return exact GROUP BY totals along with sorted doc_id and order references."""
    with _connect(db_path) as conn:
        rows = conn.execute(AGGREGATION_SQL).fetchall()
    result: List[Dict[str, Any]] = []
    for row in rows:
        doc_ids = sorted(int(item) for item in str(row["doc_ids"]).split(",") if item)
        order_refs = sorted(item for item in str(row["order_references"]).split(",") if item)
        result.append(
            {
                "specialty_code": row["specialty_code"],
                "specialty_name": row["specialty_name"],
                "education_level": row["education_level"],
                "financing_type": row["financing_type"],
                "admission_stage": row["admission_stage"],
                "total_enrolled": int(row["total_enrolled"]),
                "record_count": int(row["record_count"]),
                "doc_ids": doc_ids,
                "order_references": order_refs,
            }
        )
    return result


def test_schema_initialization_fresh_and_existing_db(tmp_path: Path) -> None:
    db_path = tmp_path / "contingent.db"
    init_schema(db_path)
    # Re-running schema initialization on an existing DB must be idempotent.
    init_schema(db_path)

    with _connect(db_path) as conn:
        doc_cols = {r["name"] for r in conn.execute("PRAGMA table_info(uploaded_documents)")}
        rec_cols = {r["name"] for r in conn.execute("PRAGMA table_info(admission_records)")}
        fk_rows = list(conn.execute("PRAGMA foreign_key_list(admission_records)"))

    assert doc_cols == {"id", "filename", "uploaded_at", "raw_text", "doc_type", "content_hash"}
    assert rec_cols == {
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
    }
    assert len(fk_rows) == 1
    assert fk_rows[0]["table"] == "uploaded_documents"
    assert fk_rows[0]["from"] == "doc_id"
    assert fk_rows[0]["to"] == "id"


def test_foreign_key_and_check_constraints_enforced(tmp_path: Path) -> None:
    db_path = tmp_path / "contingent.db"
    init_schema(db_path)

    with pytest.raises(sqlite3.IntegrityError):
        insert_admission_record(
            db_path,
            doc_id=9999,
            order_number="Пр-10",
            order_date="2026-08-20",
            education_level="ординатура",
            specialty_code="31.08.01",
            specialty_name="Акушерство и гинекология",
            financing_type="бюджет",
            admission_stage="основной",
            enrolled_count=3,
            student_identifiers=["ID-1", "ID-2", "ID-3"],
        )

    doc = upsert_uploaded_document(
        db_path,
        filename="Svedeniya_o_zachislenii_01.pdf",
        uploaded_at="2026-08-20T10:00:00Z",
        raw_text="Приказ Пр-10",
        doc_type="zachislenie",
    )
    with pytest.raises(sqlite3.IntegrityError):
        insert_admission_record(
            db_path,
            doc_id=doc["doc_id"],
            order_number="Пр-10",
            order_date="2026-08-20",
            education_level="бакалавриат",
            specialty_code="31.08.01",
            specialty_name="Акушерство и гинекология",
            financing_type="бюджет",
            admission_stage="основной",
            enrolled_count=1,
            student_identifiers=["ID-1"],
        )


def test_idempotent_deduplication_prevents_inflation(tmp_path: Path) -> None:
    db_path = tmp_path / "contingent.db"
    init_schema(db_path)

    first_doc = upsert_uploaded_document(
        db_path,
        filename="Svedeniya_o_zachislenii_1.pdf",
        uploaded_at="2026-08-20T10:00:00Z",
        raw_text="Одинаковый текст приказа",
        doc_type="zachislenie",
    )
    dup_doc = upsert_uploaded_document(
        db_path,
        filename="Svedeniya_o_zachislenii_10.pdf",
        uploaded_at="2026-08-21T10:00:00Z",
        raw_text="Одинаковый текст приказа",
        doc_type="zachislenie",
    )
    assert first_doc["inserted"] is True
    assert first_doc["deduplicated"] is False
    assert dup_doc["inserted"] is False
    assert dup_doc["deduplicated"] is True
    assert dup_doc["doc_id"] == first_doc["doc_id"]

    other_doc = upsert_uploaded_document(
        db_path,
        filename="Svedeniya_o_zachislenii_11.pdf",
        uploaded_at="2026-08-22T10:00:00Z",
        raw_text="Копия файла с другим метаданным заголовком",
        doc_type="zachislenie",
    )
    first_rec = insert_admission_record(
        db_path,
        doc_id=first_doc["doc_id"],
        order_number="Пр-101",
        order_date="2026-08-20",
        education_level="ординатура",
        specialty_code="31.08.02",
        specialty_name="Анестезиология-реаниматология",
        financing_type="целевая квота",
        admission_stage="основной",
        enrolled_count=4,
        student_identifiers=["1001", "1002", "1003", "1004"],
    )
    dup_rec = insert_admission_record(
        db_path,
        doc_id=other_doc["doc_id"],
        order_number="Пр-101",
        order_date="2026-08-20",
        education_level="ординатура",
        specialty_code="31.08.02",
        specialty_name="Анестезиология-реаниматология",
        financing_type="целевая квота",
        admission_stage="основной",
        enrolled_count=4,
        student_identifiers=["1001", "1002", "1003", "1004"],
    )
    assert first_rec["inserted"] is True
    assert dup_rec["inserted"] is False
    assert dup_rec["deduplicated"] is True
    assert dup_rec["record_id"] == first_rec["record_id"]

    totals = aggregate_admissions(db_path)
    assert len(totals) == 1
    assert totals[0]["total_enrolled"] == 4
    assert totals[0]["record_count"] == 1


def test_deterministic_group_by_aggregation_and_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "contingent.db"
    init_schema(db_path)

    d1 = upsert_uploaded_document(
        db_path,
        filename="Svedeniya_o_zachislenii_main.pdf",
        uploaded_at="2026-08-18T09:00:00Z",
        raw_text="Основной этап зачисления",
        doc_type="zachislenie",
    )
    d2 = upsert_uploaded_document(
        db_path,
        filename="Svedeniya_o_zachislenii_extra.pdf",
        uploaded_at="2026-08-25T09:00:00Z",
        raw_text="Дополнительный приказ по той же специальности",
        doc_type="zachislenie",
    )

    insert_admission_record(
        db_path,
        doc_id=d1["doc_id"],
        order_number="Пр-201",
        order_date="2026-08-18",
        education_level="ординатура",
        specialty_code="31.08.49",
        specialty_name="Терапия",
        financing_type="бюджет",
        admission_stage="основной",
        enrolled_count=5,
        student_identifiers=["A1", "A2", "A3", "A4", "A5"],
    )
    insert_admission_record(
        db_path,
        doc_id=d2["doc_id"],
        order_number="Пр-205",
        order_date="2026-08-25",
        education_level="ординатура",
        specialty_code="31.08.49",
        specialty_name="Терапия",
        financing_type="бюджет",
        admission_stage="основной",
        enrolled_count=2,
        student_identifiers=["A6", "A7"],
    )
    insert_admission_record(
        db_path,
        doc_id=d2["doc_id"],
        order_number="Пр-206",
        order_date="2026-08-25",
        education_level="аспирантура",
        specialty_code="3.1.18",
        specialty_name="Внутренние болезни",
        financing_type="договор",
        admission_stage="допконкурс",
        enrolled_count=1,
        student_identifiers=["B1"],
    )

    # Verify survival across fresh connection reads.
    totals = aggregate_admissions(db_path)
    assert totals == [
        {
            "specialty_code": "3.1.18",
            "specialty_name": "Внутренние болезни",
            "education_level": "аспирантура",
            "financing_type": "договор",
            "admission_stage": "допконкурс",
            "total_enrolled": 1,
            "record_count": 1,
            "doc_ids": [d2["doc_id"]],
            "order_references": ["Пр-206 (2026-08-25)"],
        },
        {
            "specialty_code": "31.08.49",
            "specialty_name": "Терапия",
            "education_level": "ординатура",
            "financing_type": "бюджет",
            "admission_stage": "основной",
            "total_enrolled": 7,
            "record_count": 2,
            "doc_ids": [d1["doc_id"], d2["doc_id"]],
            "order_references": ["Пр-201 (2026-08-18)", "Пр-205 (2026-08-25)"],
        },
    ]
