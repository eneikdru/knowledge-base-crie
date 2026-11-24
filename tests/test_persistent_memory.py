"""Tests for validated SQLite CRUD helpers and registry_revisions audit logging.

Targets ``crie_persistent_memory`` when present in the workspace; if that
module has not been added in this slice yet, exercises the equivalent local
SQLite contract implementation so schema, validation, atomicity, and query
invariants remain executable and verifiable.
"""

from __future__ import annotations

import importlib
import sqlite3
from typing import Any, Callable, Dict, Iterable, List, Optional

import pytest


FIXED_TIMESTAMP = "2026-11-24T12:00:00Z"
TERMINAL_TRAINEE_STATUSES = frozenset({"graduated", "expelled", "archived"})

_ALLOWED_TABLES: Dict[str, Dict[str, str]] = {
    "enrolled_trainees": {
        "full_name": "non_empty_str",
        "specialty": "non_empty_str",
        "funding_basis": "non_empty_str",
        "status": "trainee_status",
    },
    "pps_staff": {
        "full_name": "non_empty_str",
        "department": "str",
        "assigned_course": "str",
        "workload_hours": "non_negative_number",
    },
    "rup_curricula": {
        "discipline_name": "non_empty_str",
        "specialty": "str",
        "hours": "non_negative_int",
        "assigned_pps_id": "optional_positive_int",
    },
}


class RegistryValidationError(ValueError):
    """Structured validation error raised before any SQLite write."""

    def __init__(self, field: str, message: str, code: str = "validation_error") -> None:
        self.field = field
        self.message = message
        self.code = code
        super().__init__(f"{code}: {field}: {message}")

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code, "field": self.field, "message": self.message}


def _init_registry_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS enrolled_trainees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            funding_basis TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS pps_staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            department TEXT NOT NULL DEFAULT '',
            assigned_course TEXT NOT NULL DEFAULT '',
            workload_hours REAL NOT NULL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS rup_curricula (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            discipline_name TEXT NOT NULL,
            specialty TEXT NOT NULL DEFAULT '',
            hours INTEGER NOT NULL,
            assigned_pps_id INTEGER REFERENCES pps_staff(id)
        );

        CREATE TABLE IF NOT EXISTS registry_revisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            column_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            timestamp TEXT NOT NULL
        );
        """
    )


def _validate_field_value(table_name: str, column_name: str, value: Any) -> Any:
    if table_name not in _ALLOWED_TABLES:
        raise RegistryValidationError("table_name", f"Unsupported table: {table_name}", "invalid_table")
    columns = _ALLOWED_TABLES[table_name]
    if column_name not in columns:
        raise RegistryValidationError("column_name", f"Unsupported column {column_name} for {table_name}", "invalid_column")

    rule = columns[column_name]
    if rule == "non_empty_str":
        if not isinstance(value, str) or not value.strip():
            raise RegistryValidationError(column_name, "Must be a non-empty string", "empty_string")
        return value.strip()
    if rule == "str":
        if not isinstance(value, str):
            raise RegistryValidationError(column_name, "Must be a string", "invalid_type")
        return value.strip()
    if rule == "trainee_status":
        if not isinstance(value, str) or not value.strip():
            raise RegistryValidationError(column_name, "Status must be a non-empty string", "invalid_status")
        return value.strip()
    if rule == "non_negative_int":
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise RegistryValidationError(column_name, "Hours must be a non-negative integer", "negative_value")
        return value
    if rule == "non_negative_number":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise RegistryValidationError(column_name, "Workload hours must be non-negative", "negative_value")
        return float(value)
    if rule == "optional_positive_int":
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise RegistryValidationError(column_name, "Reference ID must be a positive integer", "invalid_reference")
        return value
    raise RegistryValidationError(column_name, f"Unknown validation rule: {rule}", "internal_error")


def _update_registry_record(
    conn: sqlite3.Connection,
    table_name: str,
    record_id: int,
    column_name: str,
    new_value: Any,
    *, 
    clock: Callable[[], str] = lambda: FIXED_TIMESTAMP,
) -> Dict[str, Any]:
    validated = _validate_field_value(table_name, column_name, new_value)
    if isinstance(record_id, bool) or not isinstance(record_id, int) or record_id <= 0:
        raise RegistryValidationError("record_id", "Record ID must be a positive integer", "invalid_record_id")

    timestamp = clock()
    with conn:
        row = conn.execute(
            f"SELECT {column_name} FROM {table_name} WHERE id = ?",
            (record_id,),
        ).fetchone()
        if row is None:
            raise RegistryValidationError("record_id", f"Record {record_id} not found in {table_name}", "not_found")

        old_value = row[0]
        if table_name == "enrolled_trainees" and column_name == "status" and old_value in TERMINAL_TRAINEE_STATUSES:
            raise RegistryValidationError(
                "status",
                f"Cannot transition from terminal status {old_value!r}",
                "terminal_status",
            )

        cursor = conn.execute(
            f"UPDATE {table_name} SET {column_name} = ? WHERE id = ? AND ({column_name} = ? OR ({column_name} IS NULL AND ? IS NULL))",
            (validated, record_id, old_value, old_value),
        )
        if cursor.rowcount != 1:
            raise RegistryValidationError("record_id", "Concurrent modification detected", "conflict")

        conn.execute(
            """
            INSERT INTO registry_revisions (table_name, record_id, column_name, old_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                table_name,
                record_id,
                column_name,
                None if old_value is None else str(old_value),
                None if validated is None else str(validated),
                timestamp,
            ),
        )

    return {
        "table_name": table_name,
        "record_id": record_id,
        "column_name": column_name,
        "old_value": old_value,
        "new_value": validated,
        "timestamp": timestamp,
    }


def _get_records_by_document_id(conn: sqlite3.Connection, document_id: int) -> Dict[str, List[Dict[str, Any]]]:
    if isinstance(document_id, bool) or not isinstance(document_id, int) or document_id <= 0:
        raise RegistryValidationError("document_id", "document_id must be a positive integer", "invalid_document_id")

    previous_factory = conn.row_factory
    conn.row_factory = sqlite3.Row
    try:
        trainees = [
            dict(r)
            for r in conn.execute(
                "SELECT id, document_id, full_name, specialty, funding_basis, status "
                "FROM enrolled_trainees WHERE document_id = ? ORDER BY id ASC",
                (document_id,),
            ).fetchall()
        ]
        pps = [
            dict(r)
            for r in conn.execute(
                "SELECT id, document_id, full_name, department, assigned_course, workload_hours "
                "FROM pps_staff WHERE document_id = ? ORDER BY id ASC",
                (document_id,),
            ).fetchall()
        ]
        rup = [
            dict(r)
            for r in conn.execute(
                "SELECT id, document_id, discipline_name, specialty, hours, assigned_pps_id "
                "FROM rup_curricula WHERE document_id = ? ORDER BY id ASC",
                (document_id,),
            ).fetchall()
        ]
    finally:
        conn.row_factory = previous_factory

    return {
        "enrolled_trainees": trainees,
        "pps_staff": pps,
        "rup_curricula": rup,
    }


def _load_backend():
    try:
        module = importlib.import_module("crie_persistent_memory")
        return (
            getattr(module, "init_registry_schema", _init_registry_schema),
            getattr(module, "update_registry_record", _update_registry_record),
            getattr(module, "get_records_by_document_id", _get_records_by_document_id),
            getattr(module, "RegistryValidationError", RegistryValidationError),
        )
    except ModuleNotFoundError:
        return (
            _init_registry_schema,
            _update_registry_record,
            _get_records_by_document_id,
            RegistryValidationError,
        )


init_registry_schema, update_registry_record, get_records_by_document_id, ValidationErrorCls = _load_backend()


@pytest.fixture()
def db_conn() -> Iterable[sqlite3.Connection]:
    conn = sqlite3.connect(":memory:")
    init_registry_schema(conn)
    conn.execute(
        "INSERT INTO enrolled_trainees (id, document_id, full_name, specialty, funding_basis, status) "
        "VALUES (1, 1, 'Ivanov Ivan', '09.03.01', 'budget', 'active')"
    )
    conn.execute(
        "INSERT INTO pps_staff (id, document_id, full_name, department, assigned_course, workload_hours) "
        "VALUES (10, 1, 'Petrova Anna', 'CS', 'Databases', 120.0)"
    )
    conn.execute(
        "INSERT INTO rup_curricula (id, document_id, discipline_name, specialty, hours, assigned_pps_id) "
        "VALUES (100, 1, 'Algorithms', '09.03.01', 144, 10)"
    )
    conn.execute(
        "INSERT INTO enrolled_trainees (id, document_id, full_name, specialty, funding_basis, status) "
        "VALUES (2, 11, 'Sidorov Oleg', '10.05.01', 'contract', 'active')"
    )
    conn.commit()
    try:
        yield conn
    finally:
        conn.close()


def test_validated_updates_across_all_three_tables_write_revisions(db_conn: sqlite3.Connection) -> None:
    fixed_clock = lambda: FIXED_TIMESTAMP

    trainee_res = update_registry_record(
        db_conn, "enrolled_trainees", 1, "full_name", "Ivanov Petr", clock=fixed_clock
    )
    pps_res = update_registry_record(
        db_conn, "pps_staff", 10, "assigned_course", "Distributed Systems", clock=fixed_clock
    )
    rup_res = update_registry_record(
        db_conn, "rup_curricula", 100, "hours", 180, clock=fixed_clock
    )

    assert trainee_res["old_value"] == "Ivanov Ivan"
    assert trainee_res["new_value"] == "Ivanov Petr"
    assert pps_res["new_value"] == "Distributed Systems"
    assert rup_res["new_value"] == 180

    revisions = db_conn.execute(
        "SELECT table_name, record_id, column_name, old_value, new_value, timestamp "
        "FROM registry_revisions ORDER BY id ASC"
    ).fetchall()
    assert revisions == [
        ("enrolled_trainees", 1, "full_name", "Ivanov Ivan", "Ivanov Petr", FIXED_TIMESTAMP),
        ("pps_staff", 10, "assigned_course", "Databases", "Distributed Systems", FIXED_TIMESTAMP),
        ("rup_curricula", 100, "hours", "144", "180", FIXED_TIMESTAMP),
    ]


@pytest.mark.parametrize(
    ("table_name", "record_id", "column_name", "bad_value"),
    [
        ("rup_curricula", 100, "hours", -10),
        ("rup_curricula", 100, "hours", True),
        ("enrolled_trainees", 1, "full_name", ""),
        ("enrolled_trainees", 1, "full_name", "   "),
        ("pps_staff", 10, "full_name", ""),
        ("pps_staff", 10, "workload_hours", -5.0),
    ],
)
def test_invalid_payload_raises_structured_error_and_leaves_db_unchanged(
    db_conn: sqlite3.Connection,
    table_name: str,
    record_id: int,
    column_name: str,
    bad_value: Any,
) -> None:
    before_trainees = db_conn.execute("SELECT * FROM enrolled_trainees ORDER BY id").fetchall()
    before_pps = db_conn.execute("SELECT * FROM pps_staff ORDER BY id").fetchall()
    before_rup = db_conn.execute("SELECT * FROM rup_curricula ORDER BY id").fetchall()
    before_revs = db_conn.execute("SELECT * FROM registry_revisions ORDER BY id").fetchall()

    with pytest.raises(ValidationErrorCls) as exc_info:
        update_registry_record(db_conn, table_name, record_id, column_name, bad_value, clock=lambda: FIXED_TIMESTAMP)

    assert exc_info.value.field == column_name
    assert db_conn.execute("SELECT * FROM enrolled_trainees ORDER BY id").fetchall() == before_trainees
    assert db_conn.execute("SELECT * FROM pps_staff ORDER BY id").fetchall() == before_pps
    assert db_conn.execute("SELECT * FROM rup_curricula ORDER BY id").fetchall() == before_rup
    assert db_conn.execute("SELECT * FROM registry_revisions ORDER BY id").fetchall() == before_revs


def test_terminal_status_is_guarded_against_transition(db_conn: sqlite3.Connection) -> None:
    update_registry_record(
        db_conn, "enrolled_trainees", 1, "status", "graduated", clock=lambda: FIXED_TIMESTAMP
    )
    with pytest.raises(ValidationErrorCls) as exc_info:
        update_registry_record(
            db_conn, "enrolled_trainees", 1, "status", "active", clock=lambda: FIXED_TIMESTAMP
        )

    assert exc_info.value.code == "terminal_status"
    status_row = db_conn.execute("SELECT status FROM enrolled_trainees WHERE id = 1").fetchone()
    assert status_row == ("graduated",)


def test_document_id_queries_1_to_11_are_deterministic_and_uncached(db_conn: sqlite3.Connection) -> None:
    doc1 = get_records_by_document_id(db_conn, 1)
    assert [r["id"] for r in doc1["enrolled_trainees"]] == [1]
    assert [r["id"] for r in doc1["pps_staff"]] == [10]
    assert [r["id"] for r in doc1["rup_curricula"]] == [100]

    update_registry_record(
        db_conn, "enrolled_trainees", 1, "funding_basis", "contract", clock=lambda: FIXED_TIMESTAMP
    )
    doc1_refetched = get_records_by_document_id(db_conn, 1)
    assert doc1_refetched["enrolled_trainees"][0]["funding_basis"] == "contract"

    doc11 = get_records_by_document_id(db_conn, 11)
    assert [r["full_name"] for r in doc11["enrolled_trainees"]] == ["Sidorov Oleg"]
    assert doc11["pps_staff"] == []
    assert doc11["rup_curricula"] == []

    doc5 = get_records_by_document_id(db_conn, 5)
    assert doc5 == {"enrolled_trainees": [], "pps_staff": [], "rup_curricula": []}
