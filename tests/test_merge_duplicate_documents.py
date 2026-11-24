"""Tests for document hash schema migration and transactional duplicate merging."""

from __future__ import annotations

import hashlib
import sqlite3
import unicodedata
from pathlib import Path
from typing import Iterable

import pytest

CHILD_TABLES = ("enrolled_trainees", "pps_staff", "rup_curricula")


def compute_content_sha256(raw_bytes: bytes) -> str:
    """Return deterministic lowercase hex SHA-256 digest for raw document bytes."""
    return hashlib.sha256(raw_bytes).hexdigest()


def normalize_filename(filename: str) -> str:
    """Normalize filename using basename, NFKC normalization, trimming, and lowercasing."""
    name = Path(filename.strip()).name
    return unicodedata.normalize("NFKC", name).strip().lower()


def ensure_document_hash_schema(conn: sqlite3.Connection) -> None:
    """Idempotently add hash/metadata columns and index to the documents table."""
    existing_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(documents)").fetchall()
    }
    column_defs = {
        "content_sha256": "TEXT",
        "normalized_filename": "TEXT",
        "text_size": "INTEGER",
    }
    for col_name, col_type in column_defs.items():
        if col_name not in existing_columns:
            conn.execute(f"ALTER TABLE documents ADD COLUMN {col_name} {col_type}")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_content_sha256 "
        "ON documents(content_sha256)"
    )


def merge_duplicate_documents(
    conn: sqlite3.Connection,
    canonical_id: int = 1,
    duplicate_ids: Iterable[int] = (10, 11),
    raw_content: bytes | None = None,
    fail_after_remap: bool = False,
) -> dict[str, int]:
    """Atomically merge duplicate document IDs into canonical_id and backfill SHA-256."""
    dup_list = [doc_id for doc_id in duplicate_ids if doc_id != canonical_id]
    ensure_document_hash_schema(conn)

    remapped_counts = {table: 0 for table in CHILD_TABLES}
    deleted_docs = 0

    conn.execute("BEGIN IMMEDIATE")
    try:
        canonical_row = conn.execute(
            "SELECT id, filename, content_text, content_sha256, normalized_filename, text_size "
            "FROM documents WHERE id = ?",
            (canonical_id,),
        ).fetchone()
        if canonical_row is None:
            raise ValueError(f"Canonical document ID {canonical_id} does not exist")

        _, filename, content_text, existing_sha, existing_norm, existing_size = canonical_row
        present_dups = []
        if dup_list:
            placeholders = ",".join("?" for _ in dup_list)
            present_dups = [
                row[0]
                for row in conn.execute(
                    f"SELECT id FROM documents WHERE id IN ({placeholders})",
                    dup_list,
                ).fetchall()
            ]

        if present_dups:
            dup_placeholders = ",".join("?" for _ in present_dups)
            for table in CHILD_TABLES:
                cur = conn.execute(
                    f"UPDATE {table} SET document_id = ? WHERE document_id IN ({dup_placeholders})",
                    [canonical_id, *present_dups],
                )
                remapped_counts[table] = cur.rowcount

            if fail_after_remap:
                raise RuntimeError("Simulated failure mid-transaction")

            cur = conn.execute(
                f"DELETE FROM documents WHERE id IN ({dup_placeholders})",
                present_dups,
            )
            deleted_docs = cur.rowcount

        payload_bytes = (
            raw_content
            if raw_content is not None
            else (content_text or "").encode("utf-8")
        )
        backfilled_sha = existing_sha or compute_content_sha256(payload_bytes)
        backfilled_norm = existing_norm or normalize_filename(filename or "")
        backfilled_size = (
            existing_size if existing_size is not None else len(content_text or "")
        )

        conn.execute(
            "UPDATE documents "
            "SET content_sha256 = ?, normalized_filename = ?, text_size = ? "
            "WHERE id = ?",
            (backfilled_sha, backfilled_norm, backfilled_size, canonical_id),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return {"deleted_docs": deleted_docs, **remapped_counts}


def _create_legacy_db(db_path: Path) -> sqlite3.Connection:
    """Create a pre-migration SQLite database with documents 1, 10, 11 and child rows."""
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            content_text TEXT NOT NULL
        );
        CREATE TABLE enrolled_trainees (
            id INTEGER PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id),
            trainee_name TEXT NOT NULL
        );
        CREATE TABLE pps_staff (
            id INTEGER PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id),
            staff_name TEXT NOT NULL
        );
        CREATE TABLE rup_curricula (
            id INTEGER PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id),
            program_code TEXT NOT NULL
        );

        INSERT INTO documents (id, filename, content_text) VALUES
            (1, '  Plan_2026.PDF ', 'Canonical curriculum payload'),
            (2, 'Other_Doc.pdf', 'Unrelated document payload'),
            (10, 'Plan_2026.pdf', 'Canonical curriculum payload'),
            (11, 'Plan_2026 (1).pdf', 'Canonical curriculum payload');

        INSERT INTO enrolled_trainees (id, document_id, trainee_name) VALUES
            (101, 1, 'Alice'),
            (102, 10, 'Bob'),
            (103, 11, 'Charlie'),
            (104, 2, 'Diana');

        INSERT INTO pps_staff (id, document_id, staff_name) VALUES
            (201, 10, 'Prof. Ivanov'),
            (202, 11, 'Prof. Petrova'),
            (203, 2, 'Prof. Sidorov');

        INSERT INTO rup_curricula (id, document_id, program_code) VALUES
            (301, 1, 'RUP-01'),
            (302, 10, 'RUP-02'),
            (303, 11, 'RUP-03'),
            (304, 2, 'RUP-OTHER');
        """
    )
    return conn


def test_merge_duplicate_documents_remaps_fks_and_backfills_sha256(tmp_path: Path) -> None:
    """Verify IDs 10 and 11 merge atomically into ID 1 without orphaned child rows."""
    db_path = tmp_path / "crie_documents.db"
    conn = _create_legacy_db(db_path)
    try:
        raw_pdf_bytes = b"%PDF-1.4 deterministic curriculum stream"
        result = merge_duplicate_documents(
            conn,
            canonical_id=1,
            duplicate_ids=(10, 11),
            raw_content=raw_pdf_bytes,
        )

        assert result == {
            "deleted_docs": 2,
            "enrolled_trainees": 2,
            "pps_staff": 2,
            "rup_curricula": 2,
        }

        doc_ids = [row[0] for row in conn.execute("SELECT id FROM documents ORDER BY id").fetchall()]
        assert doc_ids == [1, 2]

        canonical = conn.execute(
            "SELECT content_sha256, normalized_filename, text_size FROM documents WHERE id = 1"
        ).fetchone()
        assert canonical == (
            compute_content_sha256(raw_pdf_bytes),
            "plan_2026.pdf",
            len("Canonical curriculum payload"),
        )

        indexes = {row[1] for row in conn.execute("PRAGMA index_list(documents)").fetchall()}
        assert "idx_documents_content_sha256" in indexes

        for table in CHILD_TABLES:
            orphans = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE document_id NOT IN (SELECT id FROM documents)"
            ).fetchone()[0]
            assert orphans == 0

            doc2_count = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE document_id = 2"
            ).fetchone()[0]
            assert doc2_count == 1

        assert conn.execute(
            "SELECT COUNT(*) FROM enrolled_trainees WHERE document_id = 1"
        ).fetchone()[0] == 3
        assert conn.execute(
            "SELECT COUNT(*) FROM pps_staff WHERE document_id = 1"
        ).fetchone()[0] == 2
        assert conn.execute(
            "SELECT COUNT(*) FROM rup_curricula WHERE document_id = 1"
        ).fetchone()[0] == 3
    finally:
        conn.close()


def test_merge_duplicate_documents_is_idempotent(tmp_path: Path) -> None:
    """Verify re-running migration and merge completes without errors or record loss."""
    db_path = tmp_path / "crie_documents_idempotent.db"
    conn = _create_legacy_db(db_path)
    try:
        raw_pdf_bytes = b"%PDF-1.4 deterministic curriculum stream"
        first = merge_duplicate_documents(
            conn,
            canonical_id=1,
            duplicate_ids=(10, 11),
            raw_content=raw_pdf_bytes,
        )
        second = merge_duplicate_documents(
            conn,
            canonical_id=1,
            duplicate_ids=(10, 11),
            raw_content=raw_pdf_bytes,
        )

        assert first["deleted_docs"] == 2
        assert second == {
            "deleted_docs": 0,
            "enrolled_trainees": 0,
            "pps_staff": 0,
            "rup_curricula": 0,
        }
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM enrolled_trainees").fetchone()[0] == 4
        assert conn.execute("SELECT COUNT(*) FROM pps_staff").fetchone()[0] == 3
        assert conn.execute("SELECT COUNT(*) FROM rup_curricula").fetchone()[0] == 4
    finally:
        conn.close()


def test_merge_duplicate_documents_rolls_back_on_error(tmp_path: Path) -> None:
    """Verify mid-transaction failure leaves documents and child FKs untouched."""
    db_path = tmp_path / "crie_documents_rollback.db"
    conn = _create_legacy_db(db_path)
    try:
        with pytest.raises(RuntimeError, match="Simulated failure mid-transaction"):
            merge_duplicate_documents(
                conn,
                canonical_id=1,
                duplicate_ids=(10, 11),
                fail_after_remap=True,
            )

        doc_ids = [row[0] for row in conn.execute("SELECT id FROM documents ORDER BY id").fetchall()]
        assert doc_ids == [1, 2, 10, 11]
        assert conn.execute(
            "SELECT COUNT(*) FROM enrolled_trainees WHERE document_id IN (10, 11)"
        ).fetchone()[0] == 2
        assert conn.execute(
            "SELECT COUNT(*) FROM pps_staff WHERE document_id IN (10, 11)"
        ).fetchone()[0] == 2
        assert conn.execute(
            "SELECT COUNT(*) FROM rup_curricula WHERE document_id IN (10, 11)"
        ).fetchone()[0] == 2
    finally:
        conn.close()
