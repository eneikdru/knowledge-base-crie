"""Tests for SQLite persistent registry CRUD, validation, and revision audit logging."""

from dataclasses import dataclass
import sqlite3
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytest


class RegistryValidationError(ValueError):
    """Structured validation error raised before any SQLite mutation occurs."""

    def __init__(self, table_name: str, field_name: str, message: str) -> None:
        self.table_name = table_name
        self.field_name = field_name
        self.message = message
        super().__init__(f"{table_name}.{field_name}: {message}")


class RecordNotFoundError(LookupError):
    """Raised when a target record cannot be updated because it does not exist or failed a guard."""


def _validate_non_empty_text(table_name: str, field_name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegistryValidationError(table_name, field_name, "must be a non-empty string")
    return value.strip()


def _validate_positive_int(table_name: str, field_name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RegistryValidationError(table_name, field_name, "must be a positive integer")
    return value


def _validate_non_negative_int(table_name: str, field_name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RegistryValidationError(table_name, field_name, "must be a non-negative integer")
    return value


ValidatorFn = Callable[[str, str, Any], Any]


@dataclass(frozen=True)
class TableSpec:
    ddl: str
    validators: Dict[str, ValidatorFn]


REGISTRY_TABLES: Dict[str, TableSpec] = {
    "enrolled_trainees": TableSpec(
        ddl="""
        CREATE TABLE IF NOT EXISTS enrolled_trainees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            funding_basis TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        )
        """,
        validators={
            "document_id": _validate_positive_int,
            "full_name": _validate_non_empty_text,
            "specialty": _validate_non_empty_text,
            "funding_basis": _validate_non_empty_text,
            "status": _validate_non_empty_text,
        },
    ),
    "pps_staff": TableSpec(
        ddl="""
        CREATE TABLE IF NOT EXISTS pps_staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            department TEXT NOT NULL,
            binding_role TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        )
        """,
        validators={
            "document_id": _validate_positive_int,
            "full_name": _validate_non_empty_text,
            "department": _validate_non_empty_text,
            "binding_role": _validate_non_empty_text,
            "status": _validate_non_empty_text,
        },
    ),
    "rup_curricula": TableSpec(
        ddl="""
        CREATE TABLE IF NOT EXISTS rup_curricula (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            discipline_name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            hours INTEGER NOT NULL CHECK (hours >= 0),
            status TEXT NOT NULL DEFAULT 'active'
        )
        """,
        validators={
            "document_id": _validate_positive_int,
            "discipline_name": _validate_non_empty_text,
            "specialty": _validate_non_empty_text,
            "hours": _validate_non_negative_int,
            "status": _validate_non_empty_text,
        },
    ),
}

REGISTRY_REVISIONS_DDL = """
CREATE TABLE IF NOT EXISTS registry_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT NOT NULL,
    timestamp TEXT NOT NULL
)
"""


class PersistentRegistryStore:
    """Contract harness for validated SQLite CRUD and atomic registry_revisions logging."""

    def __init__(self, db_path: str, clock: Callable[[], str]) -> None:
        self.db_path = db_path
        self._clock = clock
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            for spec in REGISTRY_TABLES.values():
                conn.execute(spec.ddl)
            conn.execute(REGISTRY_REVISIONS_DDL)

    @staticmethod
    def _get_table_spec(table_name: str) -> TableSpec:
        spec = REGISTRY_TABLES.get(table_name)
        if spec is None:
            raise RegistryValidationError(table_name, "table_name", "unsupported registry table")
        return spec

    @staticmethod
    def _validate_field(table_name: str, field_name: str, value: Any) -> Any:
        spec = PersistentRegistryStore._get_table_spec(table_name)
        validator = spec.validators.get(field_name)
        if validator is None:
            raise RegistryValidationError(table_name, field_name, "field is not editable")
        return validator(table_name, field_name, value)

    def insert_record(self, table_name: str, payload: Dict[str, Any]) -> int:
        spec = self._get_table_spec(table_name)
        required_fields = [k for k in spec.validators if k != "status"]
        cleaned: Dict[str, Any] = {}
        for field_name in required_fields:
            if field_name not in payload:
                raise RegistryValidationError(table_name, field_name, "missing required field")
            cleaned[field_name] = self._validate_field(table_name, field_name, payload[field_name])
        if "status" in payload:
            cleaned["status"] = self._validate_field(table_name, "status", payload["status"])

        columns = ", ".join(cleaned.keys())
        placeholders = ", ".join("?" for _ in cleaned)
        with self._connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
                tuple(cleaned.values()),
            )
            return int(cursor.lastrowid)

    def update_record_field(
        self,
        table_name: str,
        record_id: int,
        field_name: str,
        new_value: Any,
        expected_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        cleaned_value = self._validate_field(table_name, field_name, new_value)
        revision_timestamp = self._clock()

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                f"SELECT * FROM {table_name} WHERE id = ?",
                (record_id,),
            ).fetchone()
            if existing is None:
                raise RecordNotFoundError(f"{table_name}#{record_id} not found")

            old_value = existing[field_name]
            where_clause = "id = ?"
            params: Tuple[Any, ...] = (cleaned_value, record_id)
            if expected_status is not None:
                where_clause = "id = ? AND status = ?"
                params = (cleaned_value, record_id, expected_status)

            cursor = conn.execute(
                f"UPDATE {table_name} SET {field_name} = ? WHERE {where_clause}",
                params,
            )
            if cursor.rowcount != 1:
                raise RecordNotFoundError(
                    f"{table_name}#{record_id} failed atomic status guard ({expected_status})"
                )

            conn.execute(
                """
                INSERT INTO registry_revisions (
                    table_name, record_id, field_name, old_value, new_value, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    table_name,
                    record_id,
                    field_name,
                    None if old_value is None else str(old_value),
                    str(cleaned_value),
                    revision_timestamp,
                ),
            )
            updated = conn.execute(
                f"SELECT * FROM {table_name} WHERE id = ?",
                (record_id,),
            ).fetchone()
            return dict(updated)

    def fetch_by_document_id(self, document_id: int) -> Dict[str, List[Dict[str, Any]]]:
        validated_doc_id = _validate_positive_int("query", "document_id", document_id)
        result: Dict[str, List[Dict[str, Any]]] = {}
        with self._connect() as conn:
            for table_name in REGISTRY_TABLES:
                rows = conn.execute(
                    f"SELECT * FROM {table_name} WHERE document_id = ? ORDER BY id ASC",
                    (validated_doc_id,),
                ).fetchall()
                result[table_name] = [dict(row) for row in rows]
        return result

    def fetch_revisions(self, table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if table_name is None:
                rows = conn.execute(
                    "SELECT * FROM registry_revisions ORDER BY id ASC"
                ).fetchall()
            else:
                self._get_table_spec(table_name)
                rows = conn.execute(
                    "SELECT * FROM registry_revisions WHERE table_name = ? ORDER BY id ASC",
                    (table_name,),
                ).fetchall()
            return [dict(row) for row in rows]


class _FixedClock:
    def __init__(self, timestamps: List[str]) -> None:
        self._timestamps = list(timestamps)
        self._index = 0

    def __call__(self) -> str:
        value = self._timestamps[self._index]
        if self._index + 1 < len(self._timestamps):
            self._index += 1
        return value


@pytest.fixture()
def registry_store(tmp_path) -> PersistentRegistryStore:
    db_file = tmp_path / "crie_registry.sqlite3"
    clock = _FixedClock([
        "2026-11-24T12:00:01Z",
        "2026-11-24T12:00:02Z",
        "2026-11-24T12:00:03Z",
    ])
    return PersistentRegistryStore(str(db_file), clock=clock)


@pytest.mark.parametrize(
    ("table_name", "initial_payload", "field_name", "new_value", "expected_old"),
    [
        (
            "enrolled_trainees",
            {
                "document_id": 1,
                "full_name": "Ivanov Petr Sergeevich",
                "specialty": "09.03.01",
                "funding_basis": "budget",
            },
            "full_name",
            "Ivanov Petr Alekseevich",
            "Ivanov Petr Sergeevich",
        ),
        (
            "pps_staff",
            {
                "document_id": 5,
                "full_name": "Sidorova Anna Viktorovna",
                "department": "Applied Math",
                "binding_role": "lecturer",
            },
            "binding_role",
            "senior_lecturer",
            "lecturer",
        ),
        (
            "rup_curricula",
            {
                "document_id": 11,
                "discipline_name": "Databases",
                "specialty": "09.03.01",
                "hours": 72,
            },
            "hours",
            108,
            "72",
        ),
    ],
)
def test_validated_field_update_writes_atomic_revision(
    registry_store: PersistentRegistryStore,
    table_name: str,
    initial_payload: Dict[str, Any],
    field_name: str,
    new_value: Any,
    expected_old: str,
) -> None:
    record_id = registry_store.insert_record(table_name, initial_payload)
    updated = registry_store.update_record_field(
        table_name, record_id, field_name, new_value, expected_status="active"
    )

    assert updated[field_name] == new_value
    revisions = registry_store.fetch_revisions(table_name)
    assert len(revisions) == 1
    assert revisions[0]["table_name"] == table_name
    assert revisions[0]["record_id"] == record_id
    assert revisions[0]["field_name"] == field_name
    assert revisions[0]["old_value"] == expected_old
    assert revisions[0]["new_value"] == str(new_value)
    assert revisions[0]["timestamp"] == "2026-11-24T12:00:01Z"


def test_invalid_payloads_raise_validation_error_without_mutating_sqlite(
    registry_store: PersistentRegistryStore,
) -> None:
    trainee_id = registry_store.insert_record(
        "enrolled_trainees",
        {
            "document_id": 2,
            "full_name": "Petrov Oleg Ivanovich",
            "specialty": "38.03.05",
            "funding_basis": "contract",
        },
    )
    rup_id = registry_store.insert_record(
        "rup_curricula",
        {
            "document_id": 2,
            "discipline_name": "Algorithms",
            "specialty": "38.03.05",
            "hours": 144,
        },
    )

    with pytest.raises(RegistryValidationError) as trainee_exc:
        registry_store.update_record_field("enrolled_trainees", trainee_id, "full_name", "   ")
    assert trainee_exc.value.table_name == "enrolled_trainees"
    assert trainee_exc.value.field_name == "full_name"

    with pytest.raises(RegistryValidationError) as rup_exc:
        registry_store.update_record_field("rup_curricula", rup_id, "hours", -10)
    assert rup_exc.value.table_name == "rup_curricula"
    assert rup_exc.value.field_name == "hours"

    with pytest.raises(RegistryValidationError):
        registry_store.update_record_field("unknown_table", 1, "full_name", "Test")

    fetched = registry_store.fetch_by_document_id(2)
    assert fetched["enrolled_trainees"][0]["full_name"] == "Petrov Oleg Ivanovich"
    assert fetched["rup_curricula"][0]["hours"] == 144
    assert registry_store.fetch_revisions() == []


def test_document_id_queries_1_to_11_are_deterministic_and_uncached(
    registry_store: PersistentRegistryStore,
) -> None:
    for doc_id in range(1, 12):
        registry_store.insert_record(
            "enrolled_trainees",
            {
                "document_id": doc_id,
                "full_name": f"Trainee {doc_id}",
                "specialty": "09.03.04",
                "funding_basis": "budget",
            },
        )
        registry_store.insert_record(
            "pps_staff",
            {
                "document_id": doc_id,
                "full_name": f"Lecturer {doc_id}",
                "department": "CS",
                "binding_role": "advisor",
            },
        )
        registry_store.insert_record(
            "rup_curricula",
            {
                "document_id": doc_id,
                "discipline_name": f"Course {doc_id}",
                "specialty": "09.03.04",
                "hours": 36 * doc_id,
            },
        )

    first_snapshot = registry_store.fetch_by_document_id(7)
    assert len(first_snapshot["enrolled_trainees"]) == 1
    assert len(first_snapshot["pps_staff"]) == 1
    assert len(first_snapshot["rup_curricula"]) == 1
    assert first_snapshot["enrolled_trainees"][0]["full_name"] == "Trainee 7"
    assert first_snapshot["rup_curricula"][0]["hours"] == 252

    # Mutate directly in SQLite outside the store instance to confirm no stale cache exists.
    with sqlite3.connect(registry_store.db_path) as raw_conn:
        raw_conn.execute(
            "UPDATE enrolled_trainees SET funding_basis = ? WHERE document_id = ?",
            ("contract", 7),
        )

    refreshed_snapshot = registry_store.fetch_by_document_id(7)
    assert refreshed_snapshot["enrolled_trainees"][0]["funding_basis"] == "contract"
    assert registry_store.fetch_by_document_id(7) == refreshed_snapshot


def test_atomic_status_guard_blocks_stale_transition(
    registry_store: PersistentRegistryStore,
) -> None:
    trainee_id = registry_store.insert_record(
        "enrolled_trainees",
        {
            "document_id": 3,
            "full_name": "Kuznetsov Dmitry",
            "specialty": "09.03.01",
            "funding_basis": "budget",
            "status": "confirmed",
        },
    )

    with pytest.raises(RecordNotFoundError):
        registry_store.update_record_field(
            "enrolled_trainees",
            trainee_id,
            "funding_basis",
            "contract",
            expected_status="active",
        )

    assert registry_store.fetch_by_document_id(3)["enrolled_trainees"][0]["funding_basis"] == "budget"
    assert registry_store.fetch_revisions() == []
