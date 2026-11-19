"""SQLite generated document registry schema, disk verification helper, and tests."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sqlite3
from typing import Callable, Dict, Optional, Tuple, Union

import pytest


SUPPORTED_MIME_TYPES: Dict[str, str] = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".csv": "text/csv",
}

DOWNLOAD_URL_PREFIX = "/crie/api/download/"

STATUS_VERIFIED = "verified"
STATUS_REVOKED = "revoked"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS generated_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    sha256_digest TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    byte_size INTEGER NOT NULL CHECK (byte_size > 0),
    status TEXT NOT NULL DEFAULT 'verified',
    created_at TEXT NOT NULL
);
"""


class DocumentVerificationError(ValueError):
    """Raised when a generated file fails existence, size, format, or integrity checks."""


@dataclass(frozen=True)
class DocumentRecord:
    """Persisted metadata for a verified generated document."""

    filename: str
    file_path: str
    sha256_digest: str
    mime_type: str
    byte_size: int
    status: str
    created_at: str

    @property
    def download_url(self) -> str:
        """Return the canonical backend download endpoint for this verified artifact."""
        return f"{DOWNLOAD_URL_PREFIX}{self.filename}"


def compute_sha256(file_path: Path) -> str:
    """Compute the lowercase hexadecimal SHA-256 digest of a file on disk."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_file_on_disk(file_path: Union[os.PathLike, str]) -> Tuple[Path, int, str]:
    """Verify that file_path exists, is a non-empty regular file, and has a supported MIME type."""
    raw_path = os.fspath(file_path)
    if not os.path.exists(raw_path):
        raise DocumentVerificationError(f"Generated file does not exist on disk: {raw_path}")
    if not os.path.isfile(raw_path):
        raise DocumentVerificationError(f"Generated path is not a regular file: {raw_path}")

    resolved = Path(raw_path).resolve()
    extension = resolved.suffix.lower()
    mime_type = SUPPORTED_MIME_TYPES.get(extension)
    if mime_type is None:
        raise DocumentVerificationError(
            f"Unsupported generated document extension: {extension or '<none>'}"
        )

    byte_size = os.path.getsize(resolved)
    if byte_size <= 0:
        raise DocumentVerificationError(f"Generated file is zero bytes: {resolved}")

    return resolved, byte_size, mime_type


class DocumentRegistry:
    """SQLite-backed registry that records and verifies generated DOCX/CSV exports."""

    def __init__(
        self,
        db_path: Union[os.PathLike, str],
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._db_path = os.fspath(db_path)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def register_document(self, file_path: Union[os.PathLike, str]) -> DocumentRecord:
        """Validate a file on disk, hash it, and commit its registry row to SQLite."""
        resolved, byte_size, mime_type = validate_file_on_disk(file_path)
        digest = compute_sha256(resolved)
        timestamp = self._clock().astimezone(timezone.utc).isoformat()
        filename = resolved.name

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO generated_documents (
                    filename, file_path, sha256_digest, mime_type, byte_size, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(filename) DO UPDATE SET
                    file_path = excluded.file_path,
                    sha256_digest = excluded.sha256_digest,
                    mime_type = excluded.mime_type,
                    byte_size = excluded.byte_size,
                    status = excluded.status,
                    created_at = excluded.created_at
                """,
                (filename, str(resolved), digest, mime_type, byte_size, STATUS_VERIFIED, timestamp),
            )
            conn.commit()

        return DocumentRecord(
            filename=filename,
            file_path=str(resolved),
            sha256_digest=digest,
            mime_type=mime_type,
            byte_size=byte_size,
            status=STATUS_VERIFIED,
            created_at=timestamp,
        )

    def resolve_verified_download(self, filename: str) -> DocumentRecord:
        """Load a registered document and verify its disk presence and digest before serving."""
        if not filename or Path(filename).name != filename:
            raise DocumentVerificationError(f"Invalid document filename: {filename!r}")

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT filename, file_path, sha256_digest, mime_type, byte_size, status, created_at
                FROM generated_documents
                WHERE filename = ?
                """,
                (filename,),
            ).fetchone()

        if row is None:
            raise DocumentVerificationError(f"Document is not registered: {filename}")
        if row["status"] != STATUS_VERIFIED:
            raise DocumentVerificationError(
                f"Document {filename} is not downloadable in status {row['status']!r}"
            )

        resolved, actual_size, actual_mime = validate_file_on_disk(row["file_path"])
        if actual_size != row["byte_size"] or actual_mime != row["mime_type"]:
            raise DocumentVerificationError(f"Document metadata mismatch on disk for {filename}")
        if compute_sha256(resolved) != row["sha256_digest"]:
            raise DocumentVerificationError(f"Document SHA-256 digest mismatch for {filename}")

        return DocumentRecord(
            filename=row["filename"],
            file_path=row["file_path"],
            sha256_digest=row["sha256_digest"],
            mime_type=row["mime_type"],
            byte_size=row["byte_size"],
            status=row["status"],
            created_at=row["created_at"],
        )

    def revoke_document(self, filename: str) -> bool:
        """Atomically transition a verified document to revoked status."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE generated_documents
                SET status = ?
                WHERE filename = ? AND status = ?
                """,
                (STATUS_REVOKED, filename, STATUS_VERIFIED),
            )
            conn.commit()
            return cursor.rowcount == 1


FIXED_NOW = datetime(2026, 11, 19, 2, 0, 0, tzinfo=timezone.utc)


def _fixed_clock() -> datetime:
    return FIXED_NOW


def test_schema_creates_expected_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "registry.sqlite3"
    DocumentRegistry(db_path, clock=_fixed_clock)

    with sqlite3.connect(db_path) as conn:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(generated_documents)").fetchall()
        }

    assert {
        "id",
        "filename",
        "file_path",
        "sha256_digest",
        "mime_type",
        "byte_size",
        "status",
        "created_at",
    }.issubset(columns)


@pytest.mark.parametrize(
    ("filename", "payload", "expected_mime"),
    [
        (
            "kcp_2027_report.docx",
            b"PK\x03\x04fake-docx-content" * 512,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (
            "kcp_2027_table.csv",
            "year,quota\n2027,120\n".encode("utf-8"),
            "text/csv",
        ),
    ],
)
def test_register_document_commits_row_for_docx_and_csv(
    tmp_path: Path, filename: str, payload: bytes, expected_mime: str
) -> None:
    artifact = tmp_path / filename
    artifact.write_bytes(payload)
    db_path = tmp_path / "registry.sqlite3"
    registry = DocumentRegistry(db_path, clock=_fixed_clock)

    record = registry.register_document(artifact)
    expected_digest = hashlib.sha256(payload).hexdigest()

    assert record.filename == filename
    assert record.sha256_digest == expected_digest
    assert record.mime_type == expected_mime
    assert record.byte_size == len(payload)
    assert record.status == STATUS_VERIFIED
    assert record.created_at == FIXED_NOW.isoformat()
    assert record.download_url == f"/crie/api/download/{filename}"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT filename, sha256_digest, mime_type, byte_size, status, created_at "
            "FROM generated_documents WHERE filename = ?",
            (filename,),
        ).fetchone()

    assert row == (
        filename,
        expected_digest,
        expected_mime,
        len(payload),
        STATUS_VERIFIED,
        FIXED_NOW.isoformat(),
    )
    resolved = registry.resolve_verified_download(filename)
    assert resolved == record


def test_register_missing_file_raises_and_writes_no_row(tmp_path: Path) -> None:
    db_path = tmp_path / "registry.sqlite3"
    registry = DocumentRegistry(db_path, clock=_fixed_clock)
    missing = tmp_path / "missing.docx"

    with pytest.raises(DocumentVerificationError, match="does not exist"):
        registry.register_document(missing)

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM generated_documents").fetchone()[0]
    assert count == 0


def test_register_zero_byte_file_raises_and_writes_no_row(tmp_path: Path) -> None:
    db_path = tmp_path / "registry.sqlite3"
    registry = DocumentRegistry(db_path, clock=_fixed_clock)
    empty_file = tmp_path / "empty.csv"
    empty_file.write_bytes(b"")

    with pytest.raises(DocumentVerificationError, match="zero bytes"):
        registry.register_document(empty_file)

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM generated_documents").fetchone()[0]
    assert count == 0


def test_register_unsupported_extension_or_directory_raises(tmp_path: Path) -> None:
    db_path = tmp_path / "registry.sqlite3"
    registry = DocumentRegistry(db_path, clock=_fixed_clock)

    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("plain text", encoding="utf-8")
    with pytest.raises(DocumentVerificationError, match="Unsupported"):
        registry.register_document(unsupported)

    directory = tmp_path / "folder.docx"
    directory.mkdir()
    with pytest.raises(DocumentVerificationError, match="not a regular file"):
        registry.register_document(directory)


def test_resolve_verified_download_detects_tampering_and_revocation(tmp_path: Path) -> None:
    db_path = tmp_path / "registry.sqlite3"
    registry = DocumentRegistry(db_path, clock=_fixed_clock)
    artifact = tmp_path / "report.csv"
    artifact.write_bytes(b"col1,col2\n1,2\n")

    registry.register_document(artifact)

    artifact.write_bytes(b"col1,col2\n9,9\n")
    with pytest.raises(DocumentVerificationError, match="digest mismatch"):
        registry.resolve_verified_download("report.csv")

    artifact.write_bytes(b"col1,col2\n1,2\n")
    assert registry.revoke_document("report.csv") is True
    assert registry.revoke_document("report.csv") is False
    with pytest.raises(DocumentVerificationError, match="not downloadable"):
        registry.resolve_verified_download("report.csv")

    with pytest.raises(DocumentVerificationError, match="Invalid document filename"):
        registry.resolve_verified_download("../report.csv")
