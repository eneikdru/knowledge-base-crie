"""
Unit and integration tests for SQLite automated backup and disaster restoration.
"""

import os
import sqlite3
import tempfile
import unittest
from scripts.backup_restore import backup_database, restore_database


class TestBackupRestore(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.test_dir.name, "test_kb.sqlite3")
        self.snapshot_path = os.path.join(self.test_dir.name, "backup_kb.snapshot.json")
        self.restored_db_path = os.path.join(self.test_dir.name, "restored_kb.sqlite3")
        self.passphrase = "SecureSecretPassphrase2026!"

        # Initialize source test database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, title TEXT, content TEXT);")
        cursor.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, val TEXT);")
        for i in range(50):
            cursor.execute(
                "INSERT INTO documents (title, content) VALUES (?, ?);",
                (f"Doc {i}", f"Content data for document {i} with non-trivial text"),
            )
        cursor.execute("INSERT INTO metadata VALUES ('version', '1.0.0');")
        conn.commit()
        conn.close()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_backup_generates_encrypted_checksummed_snapshot(self):
        res = backup_database(self.db_path, self.snapshot_path, self.passphrase)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(os.path.exists(self.snapshot_path))
        self.assertTrue(len(res["checksum_sha256"]) == 64)

    def test_restore_recovers_exact_data_and_passes_integrity(self):
        backup_database(self.db_path, self.snapshot_path, self.passphrase)

        res = restore_database(self.snapshot_path, self.restored_db_path, self.passphrase)
        self.assertEqual(res["status"], "RESTORED")
        self.assertEqual(res["integrity"], "ok")

        # Verify table records
        conn = sqlite3.connect(self.restored_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents;")
        doc_count = cursor.fetchone()[0]
        self.assertEqual(doc_count, 50)

        cursor.execute("SELECT val FROM metadata WHERE key='version';")
        ver = cursor.fetchone()[0]
        self.assertEqual(ver, "1.0.0")

        cursor.execute("PRAGMA integrity_check;")
        self.assertEqual(cursor.fetchall(), [("ok",)])
        conn.close()

    def test_restore_from_corrupted_state_recovers_cleanly(self):
        backup_database(self.db_path, self.snapshot_path, self.passphrase)

        # Simulate corrupted target DB state
        with open(self.restored_db_path, "wb") as f:
            f.write(b"CORRUPTED_BYTES_GARBAGE_STATE_DATA_CORRUPTION_SIMULATION")

        # Restore should cleanly overwrite and verify integrity
        res = restore_database(self.snapshot_path, self.restored_db_path, self.passphrase)
        self.assertEqual(res["status"], "RESTORED")
        self.assertEqual(res["integrity"], "ok")

        conn = sqlite3.connect(self.restored_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents;")
        self.assertEqual(cursor.fetchone()[0], 50)
        cursor.execute("PRAGMA integrity_check;")
        self.assertEqual(cursor.fetchall(), [("ok",)])
        conn.close()

    def test_restore_rejects_wrong_passphrase(self):
        backup_database(self.db_path, self.snapshot_path, self.passphrase)
        with self.assertRaises(ValueError):
            restore_database(self.snapshot_path, self.restored_db_path, "WrongPassphrase")

    def test_restore_rejects_tampered_payload(self):
        backup_database(self.db_path, self.snapshot_path, self.passphrase)
        with open(self.snapshot_path, "r+") as f:
            data = f.read()
            tampered = data.replace('"payload_size":', '"payload_size": 99999,')
            f.seek(0)
            f.write(tampered)
            f.truncate()
        with self.assertRaises(ValueError):
            restore_database(self.snapshot_path, self.restored_db_path, self.passphrase)


if __name__ == "__main__":
    unittest.main()
