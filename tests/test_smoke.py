import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

TARGET_TABLES: Tuple[str, ...] = ("enrolled_trainees", "pps_staff", "rup_curricula")
_DOC_NAME_COLUMNS: Tuple[str, ...] = (
    "filename",
    "file_name",
    "name",
    "title",
    "doc_name",
    "source_file",
)
_DOC_FK_COLUMNS: Tuple[str, ...] = ("document_id", "doc_id", "source_document_id")


def _existing_tables(conn: sqlite3.Connection) -> set:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row[0] for row in rows}


def _table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return [row[1] for row in rows]


def _pick_first_present(
    columns: Iterable[str], candidates: Tuple[str, ...]
) -> Optional[str]:
    col_set = set(columns)
    for candidate in candidates:
        if candidate in col_set:
            return candidate
    return None


def _query_table_totals(
    conn: sqlite3.Connection, existing: set
) -> Dict[str, int]:
    totals: Dict[str, int] = {table: 0 for table in TARGET_TABLES}
    present_tables = [table for table in TARGET_TABLES if table in existing]
    if not present_tables:
        return totals

    union_sql = " UNION ALL ".join(
        f"SELECT '{table}' AS tbl, COUNT(*) AS cnt FROM \"{table}\""
        for table in present_tables
    )
    for table_name, count in conn.execute(union_sql).fetchall():
        totals[table_name] = int(count)
    return totals


def _query_per_document_counts(
    conn: sqlite3.Connection, existing: set
) -> Dict[str, Dict[Any, int]]:
    per_doc: Dict[str, Dict[Any, int]] = {table: {} for table in TARGET_TABLES}
    for table in TARGET_TABLES:
        if table not in existing:
            continue
        fk_col = _pick_first_present(_table_columns(conn, table), _DOC_FK_COLUMNS)
        if fk_col is None:
            continue
        rows = conn.execute(
            f'SELECT "{fk_col}", COUNT(*) FROM "{table}" WHERE "{fk_col}" IS NOT NULL GROUP BY "{fk_col}"'
        ).fetchall()
        per_doc[table] = {doc_id: int(count) for doc_id, count in rows}
    return per_doc


def summarize_sqlite_registry(
    db_source: Union[str, Path, sqlite3.Connection],
) -> Dict[str, Any]:
    """Summarize uploaded documents and row counts across core CRIE SQLite tables."""
    owns_connection = not isinstance(db_source, sqlite3.Connection)
    conn = (
        sqlite3.connect(str(db_source))
        if owns_connection
        else db_source
    )
    try:
        existing = _existing_tables(conn)
        table_counts = _query_table_totals(conn, existing)
        total_extracted_rows = sum(table_counts.values())

        if "documents" not in existing:
            return {
                "is_empty": True,
                "document_count": 0,
                "documents": [],
                "table_counts": table_counts,
                "total_extracted_rows": total_extracted_rows,
            }

        doc_columns = _table_columns(conn, "documents")
        id_col = "id" if "id" in doc_columns else "rowid"
        name_col = _pick_first_present(doc_columns, _DOC_NAME_COLUMNS)
        name_expr = f'"{name_col}"' if name_col else "''"

        doc_rows = conn.execute(
            f'SELECT "{id_col}", {name_expr} FROM "documents" ORDER BY "{id_col}" ASC'
        ).fetchall()
        per_doc_counts = _query_per_document_counts(conn, existing)

        documents = [
            {
                "id": doc_id,
                "name": doc_name or "",
                "table_counts": {
                    table: per_doc_counts[table].get(doc_id, 0)
                    for table in TARGET_TABLES
                },
            }
            for doc_id, doc_name in doc_rows
        ]
        return {
            "is_empty": len(documents) == 0,
            "document_count": len(documents),
            "documents": documents,
            "table_counts": table_counts,
            "total_extracted_rows": total_extracted_rows,
        }
    finally:
        if owns_connection:
            conn.close()


def test_normative_catalog_exists():
    catalog_path = Path("data/normative/corpus_catalog.json")
    if catalog_path.exists():
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert "total_normative_files" in data
            assert data["total_normative_files"] > 0


def test_template_registry_exists():
    registry_path = Path("data/templates/template_registry.json")
    if registry_path.exists():
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert "templates" in data
            assert len(data["templates"]) > 0


def test_synthetic_avatars_exists():
    avatars_path = Path("data/avatars/synthetic_avatars.json")
    if avatars_path.exists():
        with open(avatars_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert "avatars" in data
            assert len(data["avatars"]) > 0


def test_registry_summary_with_documents_and_extracted_rows(tmp_path: Path):
    db_path = tmp_path / "crie_registry.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(
            """
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL
            );
            CREATE TABLE enrolled_trainees (
                id INTEGER PRIMARY KEY,
                document_id INTEGER,
                full_name TEXT NOT NULL
            );
            CREATE TABLE pps_staff (
                id INTEGER PRIMARY KEY,
                document_id INTEGER,
                full_name TEXT NOT NULL
            );
            CREATE TABLE rup_curricula (
                id INTEGER PRIMARY KEY,
                document_id INTEGER,
                discipline TEXT NOT NULL
            );
            INSERT INTO documents (id, filename) VALUES
                (1, 'prikaz_ordinatura_2026.pdf'),
                (2, 'prikaz_aspirantura_2026.docx');
            INSERT INTO enrolled_trainees (id, document_id, full_name) VALUES
                (1, 1, 'Trainee One'),
                (2, 1, 'Trainee Two'),
                (3, 2, 'Trainee Three');
            INSERT INTO pps_staff (id, document_id, full_name) VALUES
                (1, 2, 'Professor One');
            INSERT INTO rup_curricula (id, document_id, discipline) VALUES
                (1, 1, 'Clinical Oncology'),
                (2, 2, 'Medical Informatics');
            """
        )

    summary = summarize_sqlite_registry(db_path)
    assert summary["is_empty"] is False
    assert summary["document_count"] == 2
    assert summary["table_counts"] == {
        "enrolled_trainees": 3,
        "pps_staff": 1,
        "rup_curricula": 2,
    }
    assert summary["total_extracted_rows"] == 6
    assert summary["documents"] == [
        {
            "id": 1,
            "name": "prikaz_ordinatura_2026.pdf",
            "table_counts": {
                "enrolled_trainees": 2,
                "pps_staff": 0,
                "rup_curricula": 1,
            },
        },
        {
            "id": 2,
            "name": "prikaz_aspirantura_2026.docx",
            "table_counts": {
                "enrolled_trainees": 1,
                "pps_staff": 1,
                "rup_curricula": 1,
            },
        },
    ]


def test_registry_summary_empty_documents_table():
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(
            """
            CREATE TABLE documents (id INTEGER PRIMARY KEY, filename TEXT NOT NULL);
            CREATE TABLE enrolled_trainees (id INTEGER PRIMARY KEY, document_id INTEGER);
            CREATE TABLE pps_staff (id INTEGER PRIMARY KEY, document_id INTEGER);
            CREATE TABLE rup_curricula (id INTEGER PRIMARY KEY, document_id INTEGER);
            """
        )
        summary = summarize_sqlite_registry(conn)
        assert summary == {
            "is_empty": True,
            "document_count": 0,
            "documents": [],
            "table_counts": {
                "enrolled_trainees": 0,
                "pps_staff": 0,
                "rup_curricula": 0,
            },
            "total_extracted_rows": 0,
        }
    finally:
        conn.close()


def test_registry_summary_missing_tables_graceful():
    conn = sqlite3.connect(":memory:")
    try:
        summary = summarize_sqlite_registry(conn)
        assert summary == {
            "is_empty": True,
            "document_count": 0,
            "documents": [],
            "table_counts": {
                "enrolled_trainees": 0,
                "pps_staff": 0,
                "rup_curricula": 0,
            },
            "total_extracted_rows": 0,
        }
    finally:
        conn.close()


def test_registry_summary_without_fk_columns():
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(
            """
            CREATE TABLE documents (id INTEGER PRIMARY KEY, title TEXT NOT NULL);
            CREATE TABLE enrolled_trainees (id INTEGER PRIMARY KEY, full_name TEXT);
            CREATE TABLE pps_staff (id INTEGER PRIMARY KEY, full_name TEXT);
            CREATE TABLE rup_curricula (id INTEGER PRIMARY KEY, discipline TEXT);
            INSERT INTO documents (id, title) VALUES (10, 'Order No. 42');
            INSERT INTO enrolled_trainees (id, full_name) VALUES (1, 'Resident A');
            """
        )
        summary = summarize_sqlite_registry(conn)
        assert summary["is_empty"] is False
        assert summary["document_count"] == 1
        assert summary["table_counts"] == {
            "enrolled_trainees": 1,
            "pps_staff": 0,
            "rup_curricula": 0,
        }
        assert summary["documents"] == [
            {
                "id": 10,
                "name": "Order No. 42",
                "table_counts": {
                    "enrolled_trainees": 0,
                    "pps_staff": 0,
                    "rup_curricula": 0,
                },
            }
        ]
    finally:
        conn.close()
