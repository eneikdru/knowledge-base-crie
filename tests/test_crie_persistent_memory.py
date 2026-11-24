"""Focused tests for persistent structured registry CRUD and revision audit logging."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Callable

import pytest

crie_persistent_memory = pytest.importorskip(
    "crie_persistent_memory",
    reason="crie_persistent_memory.py is not yet present in the repository (outside slice fileScope)",
)

FIXED_TIMESTAMP = "2026-11-24T12:00:00Z"


def _fixed_clock() -> str:
    return FIXED_TIMESTAMP


def _resolve_store(db_path: Path, clock: Callable[[], str] = _fixed_clock) -> Any:
    """Instantiate the persistent memory store with an injectable clock."""
    store_cls = getattr(crie_persistent_memory, "PersistentRegistryStore", None) or getattr(
        crie_persistent_memory, "CriePersistentMemory", None
    )
    if store_cls is None:
        pytest.fail("crie_persistent_memory must expose PersistentRegistryStore or CriePersistentMemory")
    return store_cls(str(db_path), clock=clock)


def _seed_structured_records(db_path: Path) -> None:
    """Seed deterministic baseline rows across all three structured tables for document IDs 1-11."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT INTO enrolled_trainees (id, document_id, full_name, specialty, funding_basis) "
            "VALUES (1, 1, 'Ivanov Ivan Ivanovich', 'Pedagogy', 'budget')"
        )
        conn.execute(
            "INSERT INTO enrolled_trainees (id, document_id, full_name, specialty, funding_basis) "
            "VALUES (2, 11, 'Petrova Anna Sergeevna', 'Psychology', 'paid')"
        )
        conn.execute(
            "INSERT INTO pps_staff (id, document_id, full_name, department, position) "
            "VALUES (1, 1, 'Sidorov Petr Alekseevich', 'Didactics', 'Associate Professor')"
        )
        conn.execute(
            "INSERT INTO rup_curricula (id, document_id, discipline_name, hours, pps_staff_id) "
            "VALUES (1, 1, 'Modern Pedagogy', 72, 1)"
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture()
def registry_db(tmp_path: Path) -> tuple[Path, Any]:
    db_path = tmp_path / "crie_registry.sqlite3"
    store = _resolve_store(db_path)
    store.init_schema()
    _seed_structured_records(db_path)
    return db_path, store


def test_schema_contains_structured_and_audit_tables(registry_db: tuple[Path, Any]) -> None:
    db_path, _ = registry_db
    conn = sqlite3.connect(str(db_path))
    try:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert {"enrolled_trainees", "pps_staff", "rup_curricula", "registry_revisions"} <= tables

        revision_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(registry_revisions)").fetchall()
        }
        assert {"table_name", "record_id", "old_value", "new_value", "timestamp"} <= revision_columns
    finally:
        conn.close()


@pytest.mark.parametrize(
    ("table_name", "record_id", "field_name", "new_value", "expected_old_value"),
    [
        ("enrolled_trainees", 1, "full_name", "Ivanov Ilya Ivanovich", "Ivanov Ivan Ivanovich"),
        ("pps_staff", 1, "department", "Educational Management", "Didactics"),
        ("rup_curricula", 1, "hours", 108, "72"),
    ],
)
def test_validated_field_update_is_atomic_and_audited(
    registry_db: tuple[Path, Any],
    table_name: str,
    record_id: int,
    field_name: str,
    new_value: Any,
    expected_old_value: str,
) -> None:
    db_path, store = registry_db

    store.update_record_field(
        table_name=table_name,
        record_id=record_id,
        field_name=field_name,
        new_value=new_value,
    )

    conn = sqlite3.connect(str(db_path))
    try:
        updated_row = conn.execute(
            f"SELECT {field_name} FROM {table_name} WHERE id = ?", (record_id,)
        ).fetchone()
        assert updated_row is not None
        assert str(updated_row[0]) == str(new_value)

        revisions = conn.execute(
            "SELECT table_name, record_id, old_value, new_value, timestamp "
            "FROM registry_revisions WHERE table_name = ? AND record_id = ?",
            (table_name, record_id),
        ).fetchall()
        assert len(revisions) == 1
        rev_table, rev_id, old_val, new_val, rev_ts = revisions[0]
        assert rev_table == table_name
        assert rev_id == record_id
        assert str(old_val) == expected_old_value
        assert str(new_val) == str(new_value)
        assert rev_ts == FIXED_TIMESTAMP
    finally:
        conn.close()


@pytest.mark.parametrize(
    ("table_name", "record_id", "field_name", "invalid_value"),
    [
        ("rup_curricula", 1, "hours", -10),
        ("enrolled_trainees", 1, "full_name", ""),
        ("pps_staff", 1, "full_name", "   "),
    ],
)
def test_invalid_payload_raises_structured_error_and_modifies_zero_rows(
    registry_db: tuple[Path, Any],
    table_name: str,
    record_id: int,
    field_name: str,
    invalid_value: Any,
) -> None:
    db_path, store = registry_db
    validation_error = getattr(crie_persistent_memory, "RegistryValidationError", ValueError)

    conn = sqlite3.connect(str(db_path))
    try:
        before_value = conn.execute(
            f"SELECT {field_name} FROM {table_name} WHERE id = ?", (record_id,)
        ).fetchone()[0]
        before_revisions = conn.execute("SELECT COUNT(*) FROM registry_revisions").fetchone()[0]
    finally:
        conn.close()

    with pytest.raises(validation_error):
        store.update_record_field(
            table_name=table_name,
            record_id=record_id,
            field_name=field_name,
            new_value=invalid_value,
        )

    conn = sqlite3.connect(str(db_path))
    try:
        after_value = conn.execute(
            f"SELECT {field_name} FROM {table_name} WHERE id = ?", (record_id,)
        ).fetchone()[0]
        after_revisions = conn.execute("SELECT COUNT(*) FROM registry_revisions").fetchone()[0]
        assert after_value == before_value
        assert after_revisions == before_revisions == 0
    finally:
        conn.close()


@pytest.mark.parametrize("document_id", [1, 11])
def test_fetch_linked_records_by_document_id_is_deterministic_and_uncached(
    registry_db: tuple[Path, Any], document_id: int
) -> None:
    _, store = registry_db

    first_fetch = store.get_records_by_document_id(document_id)
    second_fetch = store.get_records_by_document_id(document_id)
    assert first_fetch == second_fetch

    if document_id == 1:
        assert len(first_fetch["enrolled_trainees"]) == 1
        assert len(first_fetch["pps_staff"]) == 1
        assert len(first_fetch["rup_curricula"]) == 1

        store.update_record_field(
            table_name="enrolled_trainees",
            record_id=1,
            field_name="specialty",
            new_value="Digital Didactics",
        )
        refreshed = store.get_records_by_document_id(document_id)
        assert refreshed["enrolled_trainees"][0]["specialty"] == "Digital Didactics"
    else:
        assert len(first_fetch["enrolled_trainees"]) == 1
        assert first_fetch["enrolled_trainees"][0]["id"] == 2
        assert first_fetch["pps_staff"] == []
        assert first_fetch["rup_curricula"] == []
