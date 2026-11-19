import sqlite3
from typing import List, Tuple

import pytest

KCP_PARAMETERS_DDL = """
CREATE TABLE IF NOT EXISTS kcp_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parameter_key TEXT NOT NULL UNIQUE,
    parameter_type TEXT NOT NULL,
    name_ru TEXT NOT NULL,
    name_en TEXT NOT NULL,
    education_level TEXT,
    rg_group INTEGER,
    prior_kcp INTEGER,
    moh_limit INTEGER,
    normative_ref TEXT NOT NULL
);
"""

VERIFIED_ORDER_824_ROWS: List[Tuple] = [
    (
        "rg:residency",
        "calculation_group",
        "Ординатура",
        "Residency",
        "residency",
        5,
        None,
        None,
        "Order #824, App. 8",
    ),
    (
        "rg:postgraduate",
        "calculation_group",
        "Аспирантура",
        "Postgraduate",
        "postgraduate",
        3,
        None,
        None,
        "Order #824, App. 8",
    ),
    (
        "specialty:pediatrics",
        "specialty_kcp",
        "Педиатрия",
        "Pediatrics",
        "residency",
        5,
        7,
        7,
        "Order #824, cl. 12",
    ),
    (
        "specialty:infectious_diseases",
        "specialty_kcp",
        "Инфекционные болезни",
        "Infectious Diseases",
        "residency",
        5,
        8,
        10,
        "Order #824, cl. 12",
    ),
    (
        "specialty:epidemiology",
        "specialty_kcp",
        "Эпидемиология",
        "Epidemiology",
        "residency",
        5,
        11,
        16,
        "Order #824, cl. 12",
    ),
]


def init_kcp_parameters_schema(conn: sqlite3.Connection) -> None:
    """Create the kcp_parameters table if it does not exist."""
    conn.execute(KCP_PARAMETERS_DDL)
    conn.commit()


def seed_kcp_parameters(conn: sqlite3.Connection) -> None:
    """Idempotently seed verified Order #824 RG, prior KCP, and MoH limits."""
    conn.executemany(
        """
        INSERT OR IGNORE INTO kcp_parameters (
            parameter_key,
            parameter_type,
            name_ru,
            name_en,
            education_level,
            rg_group,
            prior_kcp,
            moh_limit,
            normative_ref
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        VERIFIED_ORDER_824_ROWS,
    )
    conn.commit()


def test_kcp_parameters_schema_and_verified_order_824_seed(tmp_path) -> None:
    db_path = tmp_path / "kcp_test.sqlite3"
    with sqlite3.connect(db_path) as conn:
        init_kcp_parameters_schema(conn)
        seed_kcp_parameters(conn)

        rows = conn.execute(
            """
            SELECT parameter_key, rg_group, prior_kcp, moh_limit
            FROM kcp_parameters
            ORDER BY id
            """
        ).fetchall()

    by_key = {
        key: {"rg_group": rg, "prior_kcp": kcp, "moh_limit": limit}
        for key, rg, kcp, limit in rows
    }

    assert len(rows) == 5
    assert by_key["rg:residency"]["rg_group"] == 5
    assert by_key["rg:postgraduate"]["rg_group"] == 3
    assert by_key["specialty:pediatrics"]["prior_kcp"] == 7
    assert by_key["specialty:pediatrics"]["moh_limit"] == 7
    assert by_key["specialty:infectious_diseases"]["prior_kcp"] == 8
    assert by_key["specialty:infectious_diseases"]["moh_limit"] == 10
    assert by_key["specialty:epidemiology"]["prior_kcp"] == 11
    assert by_key["specialty:epidemiology"]["moh_limit"] == 16


def test_kcp_parameters_seed_is_idempotent(tmp_path) -> None:
    db_path = tmp_path / "kcp_idempotent.sqlite3"
    with sqlite3.connect(db_path) as conn:
        init_kcp_parameters_schema(conn)
        seed_kcp_parameters(conn)
        seed_kcp_parameters(conn)
        init_kcp_parameters_schema(conn)
        seed_kcp_parameters(conn)

        total_count = conn.execute("SELECT COUNT(*) FROM kcp_parameters").fetchone()[0]
        distinct_keys = conn.execute(
            "SELECT COUNT(DISTINCT parameter_key) FROM kcp_parameters"
        ).fetchone()[0]

    assert total_count == 5
    assert distinct_keys == 5


def test_kcp_parameters_unique_constraint_prevents_duplicates(tmp_path) -> None:
    db_path = tmp_path / "kcp_unique.sqlite3"
    with sqlite3.connect(db_path) as conn:
        init_kcp_parameters_schema(conn)
        seed_kcp_parameters(conn)

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO kcp_parameters (
                    parameter_key,
                    parameter_type,
                    name_ru,
                    name_en,
                    education_level,
                    rg_group,
                    prior_kcp,
                    moh_limit,
                    normative_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                VERIFIED_ORDER_824_ROWS[2],
            )
