"""
Unit and integration tests for SQLite automated backup and disaster restoration.
Verifies cryptographic authentication, checksum verification, tamper rejection, and clean restoration.
"""

import json
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

        # Initialize source test database with schema and test rows
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
        self.assertEqual(len(res["checksum_sha256"]), 64)

        with open(self.snapshot_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("magic"), "CRIE_ENCRYPTED_SNAPSHOT_V1")
        self.assertIn("tag", data)
        self.assertIn("ciphertext", data)
        self.assertIn("salt", data)
        self.assertIn("nonce", data)

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
        with self.assertRaises(ValueError) as ctx:
            restore_database(self.snapshot_path, self.restored_db_path, "WrongPassphrase")
        self.assertIn("authentication failed", str(ctx.exception).lower())

    def test_restore_rejects_tampered_payload(self):
        backup_database(self.db_path, self.snapshot_path, self.passphrase)
        with open(self.snapshot_path, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["payload_size"] = 99999
            f.seek(0)
            json.dump(data, f)
            f.truncate()
        with self.assertRaises(ValueError) as ctx:
            restore_database(self.snapshot_path, self.restored_db_path, self.passphrase)
        self.assertIn("authentication failed", str(ctx.exception).lower())

    def test_restore_rejects_tampered_ciphertext(self):
        backup_database(self.db_path, self.snapshot_path, self.passphrase)
        with open(self.snapshot_path, "r+", encoding="utf-8") as f:
            data = json.load(f)
            # Tamper ciphertext by altering a base64 character
            ct = list(data["ciphertext"])
            ct[10] = "A" if ct[10] != "A" else "B"
            data["ciphertext"] = "".join(ct)
            f.seek(0)
            json.dump(data, f)
            f.truncate()
        with self.assertRaises(ValueError) as ctx:
            restore_database(self.snapshot_path, self.restored_db_path, self.passphrase)
        self.assertIn("authentication failed", str(ctx.exception).lower())

    def test_restore_rejects_tampered_tag(self):
        backup_database(self.db_path, self.snapshot_path, self.passphrase)
        with open(self.snapshot_path, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["tag"] = "0" * 64
            f.seek(0)
            json.dump(data, f)
            f.truncate()
        with self.assertRaises(ValueError) as ctx:
            restore_database(self.snapshot_path, self.restored_db_path, self.passphrase)
        self.assertIn("authentication failed", str(ctx.exception).lower())

    def test_restore_rejects_invalid_magic_header(self):
        backup_database(self.db_path, self.snapshot_path, self.passphrase)
        with open(self.snapshot_path, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["magic"] = "INVALID_HEADER_MAGIC"
            f.seek(0)
            json.dump(data, f)
            f.truncate()
        with self.assertRaises(ValueError) as ctx:
            restore_database(self.snapshot_path, self.restored_db_path, self.passphrase)
        self.assertIn("unsupported snapshot format", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
