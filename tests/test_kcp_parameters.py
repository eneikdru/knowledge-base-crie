import sqlite3
from pathlib import Path

import pytest


KCP_PARAMETERS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS kcp_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type TEXT NOT NULL CHECK (record_type IN ('rg_group', 'specialty_kcp')),
    key_code TEXT NOT NULL UNIQUE,
    name_ru TEXT NOT NULL,
    name_en TEXT NOT NULL,
    education_level TEXT,
    rg_value INTEGER,
    prior_kcp INTEGER,
    moh_limit INTEGER,
    normative_source TEXT NOT NULL DEFAULT 'Order #824, cl. 12 / App. 8'
);
"""

ORDER_824_SEED_ROWS = (
    (
        "rg_group",
        "residency",
        "Ординатура",
        "Residency",
        "residency",
        5,
        None,
        None,
        "Order #824, App. 8",
    ),
    (
        "rg_group",
        "postgraduate",
        "Аспирантура",
        "Postgraduate",
        "postgraduate",
        3,
        None,
        None,
        "Order #824, App. 8",
    ),
    (
        "specialty_kcp",
        "pediatrics",
        "Педиатрия",
        "Pediatrics",
        "residency",
        5,
        7,
        7,
        "Order #824, cl. 12",
    ),
    (
        "specialty_kcp",
        "infectious_diseases",
        "Инфекционные болезни",
        "Infectious Diseases",
        "residency",
        5,
        8,
        10,
        "Order #824, cl. 12",
    ),
    (
        "specialty_kcp",
        "epidemiology",
        "Эпидемиология",
        "Epidemiology",
        "residency",
        5,
        11,
        16,
        "Order #824, cl. 12",
    ),
)

UPSERT_KCP_PARAMETER_SQL = """
INSERT INTO kcp_parameters (
    record_type,
    key_code,
    name_ru,
    name_en,
    education_level,
    rg_value,
    prior_kcp,
    moh_limit,
    normative_source
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(key_code) DO UPDATE SET
    record_type = excluded.record_type,
    name_ru = excluded.name_ru,
    name_en = excluded.name_en,
    education_level = excluded.education_level,
    rg_value = excluded.rg_value,
    prior_kcp = excluded.prior_kcp,
    moh_limit = excluded.moh_limit,
    normative_source = excluded.normative_source;
"""


def init_kcp_parameters_table(conn: sqlite3.Connection) -> None:
    """Create the kcp_parameters table if it does not exist."""
    conn.execute(KCP_PARAMETERS_SCHEMA_SQL)
    conn.commit()


def seed_kcp_parameters(conn: sqlite3.Connection) -> None:
    """Idempotently seed verified Order #824 RG, prior KCP, and MoH limit rows."""
    init_kcp_parameters_table(conn)
    conn.executemany(UPSERT_KCP_PARAMETER_SQL, ORDER_824_SEED_ROWS)
    conn.commit()


@pytest.fixture()
def db_conn(tmp_path: Path):
    db_path = tmp_path / "kcp_parameters.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def test_kcp_parameters_seeded_with_verified_order_824_constants(db_conn: sqlite3.Connection) -> None:
    seed_kcp_parameters(db_conn)

    rows = db_conn.execute(
        "SELECT record_type, key_code, name_ru, name_en, rg_value, prior_kcp, moh_limit "
        "FROM kcp_parameters ORDER BY id"
    ).fetchall()
    by_key = {row["key_code"]: dict(row) for row in rows}

    assert len(rows) == 5

    assert by_key["residency"]["record_type"] == "rg_group"
    assert by_key["residency"]["rg_value"] == 5
    assert by_key["postgraduate"]["record_type"] == "rg_group"
    assert by_key["postgraduate"]["rg_value"] == 3

    assert by_key["pediatrics"]["prior_kcp"] == 7
    assert by_key["pediatrics"]["moh_limit"] == 7

    assert by_key["infectious_diseases"]["prior_kcp"] == 8
    assert by_key["infectious_diseases"]["moh_limit"] == 10

    assert by_key["epidemiology"]["prior_kcp"] == 11
    assert by_key["epidemiology"]["moh_limit"] == 16


def test_kcp_parameters_seeding_is_idempotent(db_conn: sqlite3.Connection) -> None:
    seed_kcp_parameters(db_conn)
    seed_kcp_parameters(db_conn)
    seed_kcp_parameters(db_conn)

    total_count = db_conn.execute("SELECT COUNT(*) FROM kcp_parameters").fetchone()[0]
    distinct_keys = db_conn.execute("SELECT COUNT(DISTINCT key_code) FROM kcp_parameters").fetchone()[0]
    specialty_count = db_conn.execute(
        "SELECT COUNT(*) FROM kcp_parameters WHERE record_type = 'specialty_kcp'"
    ).fetchone()[0]

    assert total_count == 5
    assert distinct_keys == 5
    assert specialty_count == 3


def test_kcp_parameters_enforces_unique_key_code(db_conn: sqlite3.Connection) -> None:
    seed_kcp_parameters(db_conn)

    with pytest.raises(sqlite3.IntegrityError):
        db_conn.execute(
            "INSERT INTO kcp_parameters (record_type, key_code, name_ru, name_en, prior_kcp, moh_limit) "
            "VALUES ('specialty_kcp', 'pediatrics', 'Педиатрия', 'Pediatrics', 7, 7)"
        )


def test_kcp_parameters_moh_limits_cover_prior_kcp(db_conn: sqlite3.Connection) -> None:
    seed_kcp_parameters(db_conn)

    specialty_rows = db_conn.execute(
        "SELECT key_code, prior_kcp, moh_limit FROM kcp_parameters WHERE record_type = 'specialty_kcp'"
    ).fetchall()

    assert len(specialty_rows) == 3
    for row in specialty_rows:
        assert row["prior_kcp"] is not None
        assert row["moh_limit"] is not None
        assert row["moh_limit"] >= row["prior_kcp"]
