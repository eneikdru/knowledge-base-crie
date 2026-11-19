"""Tests for the staff_pps SQLite schema, provenance rules, and idempotent seeding."""

from __future__ import annotations

import importlib
import importlib.util
import sqlite3
from pathlib import Path
from typing import Any

import pytest

REQUIRED_COLUMNS = [
    "id",
    "full_name",
    "degree",
    "title",
    "position",
    "department",
    "curated_specialties",
    "clinical_base",
    "source_order",
    "is_active",
]

FICTIONAL_DEMO_SURNAMES = ("Семенова", "Климова", "Попова")

STAFF_PPS_DDL = """
CREATE TABLE IF NOT EXISTS staff_pps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
    degree TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    position TEXT NOT NULL DEFAULT '',
    department TEXT NOT NULL DEFAULT '',
    curated_specialties TEXT NOT NULL DEFAULT '',
    clinical_base TEXT NOT NULL DEFAULT '',
    source_order TEXT NOT NULL CHECK (length(trim(source_order)) > 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    UNIQUE (full_name)
);
"""


def init_staff_pps_schema(conn: sqlite3.Connection) -> None:
    """Initialize the staff_pps table with provenance and active-flag constraints."""
    conn.execute(STAFF_PPS_DDL)
    conn.commit()


def upsert_verified_staff(conn: sqlite3.Connection, records: list[dict[str, Any]]) -> int:
    """Idempotently upsert confirmed active staff records with official order provenance."""
    validated: list[tuple[Any, ...]] = []
    for record in records:
        is_active = int(record.get("is_active", 1))
        if is_active != 1:
            continue
        full_name = str(record.get("full_name") or "").strip()
        source_order = str(record.get("source_order") or "").strip()
        if not full_name or not source_order:
            raise ValueError("Confirmed staff record requires non-empty full_name and source_order")
        validated.append(
            (
                full_name,
                str(record.get("degree") or "").strip(),
                str(record.get("title") or "").strip(),
                str(record.get("position") or "").strip(),
                str(record.get("department") or "").strip(),
                str(record.get("curated_specialties") or "").strip(),
                str(record.get("clinical_base") or "").strip(),
                source_order,
                1,
            )
        )

    with conn:
        conn.executemany(
            """
            INSERT INTO staff_pps (
                full_name,
                degree,
                title,
                position,
                department,
                curated_specialties,
                clinical_base,
                source_order,
                is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(full_name) DO UPDATE SET
                degree = excluded.degree,
                title = excluded.title,
                position = excluded.position,
                department = excluded.department,
                curated_specialties = excluded.curated_specialties,
                clinical_base = excluded.clinical_base,
                source_order = excluded.source_order,
                is_active = excluded.is_active
            """,
            validated,
        )
    return len(validated)


def _load_crie_persistent_memory() -> Any | None:
    """Return crie_persistent_memory module if present in the workspace."""
    if importlib.util.find_spec("crie_persistent_memory") is None:
        return None
    return importlib.import_module("crie_persistent_memory")


def test_staff_pps_schema_has_all_ten_required_columns(tmp_path: Path) -> None:
    """Verify staff_pps exposes all 10 required columns from id through is_active."""
    db_path = tmp_path / "staff_pps.db"
    conn = sqlite3.connect(db_path)
    try:
        init_staff_pps_schema(conn)
        columns = [row[1] for row in conn.execute("PRAGMA table_info(staff_pps)").fetchall()]
        assert columns == REQUIRED_COLUMNS
    finally:
        conn.close()

    module = _load_crie_persistent_memory()
    if module is not None and hasattr(module, "init_db"):
        mod_db = tmp_path / "module_staff_pps.db"
        module.init_db(str(mod_db))
        mod_conn = sqlite3.connect(mod_db)
        try:
            mod_columns = [row[1] for row in mod_conn.execute("PRAGMA table_info(staff_pps)").fetchall()]
            assert mod_columns == REQUIRED_COLUMNS
        finally:
            mod_conn.close()


@pytest.mark.parametrize(
    "full_name,source_order,is_active",
    [
        (None, "Приказ № 101-к", 1),
        ("   ", "Приказ № 101-к", 1),
        ("Иванов Иван Иванович", None, 1),
        ("Иванов Иван Иванович", "   ", 1),
        ("Иванов Иван Иванович", "Приказ № 101-к", 2),
    ],
)
def test_staff_pps_rejects_missing_provenance_or_invalid_active_flag(
    tmp_path: Path,
    full_name: str | None,
    source_order: str | None,
    is_active: int,
) -> None:
    """Ensure SQLite constraints reject rows missing full_name, source_order, or valid is_active."""
    conn = sqlite3.connect(tmp_path / "constraints.db")
    try:
        init_staff_pps_schema(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO staff_pps (full_name, source_order, is_active)
                VALUES (?, ?, ?)
                """,
                (full_name, source_order, is_active),
            )
    finally:
        conn.close()


def test_idempotent_seed_inserts_only_active_staff_without_duplicates(tmp_path: Path) -> None:
    """Verify idempotent seed inserts only active verified staff and updates without duplicates."""
    initial_batch = [
        {
            "full_name": "Акимкин Василий Геннадьевич",
            "degree": "д.м.н.",
            "title": "профессор, академик РАН",
            "position": "директор",
            "department": "ФБУН ЦНИИ Эпидемиологии Роспотребнадзора",
            "curated_specialties": "Эпидемиология",
            "clinical_base": "ФБУН ЦНИИЭ",
            "source_order": "Приказ Роспотребнадзора № 10-к",
            "is_active": 1,
        },
        {
            "full_name": "Архивный Сотрудник Тест",
            "degree": "к.м.н.",
            "title": "",
            "position": "преподаватель",
            "department": "Образовательный центр",
            "curated_specialties": "Инфекционные болезни",
            "clinical_base": "ФБУН ЦНИИЭ",
            "source_order": "Приказ № 12-к (архив)",
            "is_active": 0,
        },
    ]

    updated_batch = [
        {
            "full_name": "Акимкин Василий Геннадьевич",
            "degree": "д.м.н.",
            "title": "профессор, академик РАН",
            "position": "директор, заведующий кафедрой",
            "department": "ФБУН ЦНИИ Эпидемиологии Роспотребнадзора",
            "curated_specialties": "Эпидемиология, организация здравоохранения",
            "clinical_base": "ФБУН ЦНИИЭ",
            "source_order": "Приказ Роспотребнадзора № 10-к / РУП-2026",
            "is_active": 1,
        },
    ]

    conn = sqlite3.connect(tmp_path / "seed.db")
    try:
        init_staff_pps_schema(conn)
        inserted = upsert_verified_staff(conn, initial_batch)
        assert inserted == 1

        reseeded = upsert_verified_staff(conn, updated_batch)
        assert reseeded == 1

        rows = conn.execute(
            "SELECT full_name, position, source_order, is_active FROM staff_pps"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0] == (
            "Акимкин Василий Геннадьевич",
            "директор, заведующий кафедрой",
            "Приказ Роспотребнадзора № 10-к / РУП-2026",
            1,
        )
        for surname in FICTIONAL_DEMO_SURNAMES:
            assert all(surname not in row[0] for row in rows)
    finally:
        conn.close()


def test_upsert_rejects_active_record_without_order_provenance(tmp_path: Path) -> None:
    """Verify active records missing official source_order are rejected atomically."""
    conn = sqlite3.connect(tmp_path / "provenance.db")
    try:
        init_staff_pps_schema(conn)
        with pytest.raises(ValueError, match="source_order"):
            upsert_verified_staff(
                conn,
                [
                    {
                        "full_name": "Петров Петр Петрович",
                        "source_order": "",
                        "is_active": 1,
                    }
                ],
            )
        count = conn.execute("SELECT COUNT(*) FROM staff_pps").fetchone()[0]
        assert count == 0
    finally:
        conn.close()
