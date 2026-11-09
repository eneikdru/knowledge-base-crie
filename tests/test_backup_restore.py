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

        # Initialize source test database with documents, catalog and avatar state
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, title TEXT, content TEXT);")
        cursor.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, val TEXT);")
        cursor.execute(
            "CREATE TABLE catalog_items (id INTEGER PRIMARY KEY, title TEXT, category TEXT, file_path TEXT);"
        )
        cursor.execute(
            "CREATE TABLE synthetic_avatars (avatar_id TEXT PRIMARY KEY, pseudonym TEXT, role_code TEXT, department TEXT);"
        )

        for i in range(50):
            cursor.execute(
                "INSERT INTO documents (title, content) VALUES (?, ?);",
                (f"Doc {i}", f"Content data for document {i} with non-trivial text"),
            )
        cursor.execute("INSERT INTO metadata VALUES ('version', '1.0.0');")

        cursor.execute(
            "INSERT INTO catalog_items (title, category, file_path) VALUES (?, ?, ?);",
            ("РПД Эпидемиология", "05 ООП РПД 2026_27", "ООП 320812/rpd_epi.docx"),
        )
        cursor.execute(
            "INSERT INTO catalog_items (title, category, file_path) VALUES (?, ?, ?);",
            ("ФОС Педиатрия ГИА", "05 ООП ФОС", "ФОС 310819/fos_ped.docx"),
        )

        cursor.execute(
            "INSERT INTO synthetic_avatars (avatar_id, pseudonym, role_code, department) VALUES (?, ?, ?, ?);",
            ("ORD-0042", "Resident 42", "ORDINATOR", "Epidemiology"),
        )
        cursor.execute(
            "INSERT INTO synthetic_avatars (avatar_id, pseudonym, role_code, department) VALUES (?, ?, ?, ?);",
            ("FAC-0105", "Faculty 105", "DOCENT", "Infectious Diseases"),
        )

        conn.commit()
        conn.close()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_backup_generates_encrypted_checksummed_snapshot(self):
        res = backup_database(self.db_path, self.snapshot_path, self.passphrase)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(os.path.exists(self.snapshot_path))
        self.assertEqual(len(res["checksum_sha256"]), 64)

    def test_restore_recovers_exact_data_and_passes_integrity(self):
        backup_database(self.db_path, self.snapshot_path, self.passphrase)

        res = restore_database(self.snapshot_path, self.restored_db_path, self.passphrase)
        self.assertEqual(res["status"], "RESTORED")
        self.assertEqual(res["integrity"], "ok")

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

    def test_backup_and_restore_catalog_and_avatar_state(self):
        backup_database(self.db_path, self.snapshot_path, self.passphrase)
        restore_database(self.snapshot_path, self.restored_db_path, self.passphrase)

        conn = sqlite3.connect(self.restored_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT title, category, file_path FROM catalog_items ORDER BY id;")
        catalog_rows = cursor.fetchall()
        self.assertEqual(len(catalog_rows), 2)
        self.assertEqual(catalog_rows[0][0], "РПД Эпидемиология")
        self.assertEqual(catalog_rows[1][1], "05 ООП ФОС")

        cursor.execute("SELECT avatar_id, pseudonym, role_code, department FROM synthetic_avatars ORDER BY avatar_id;")
        avatar_rows = cursor.fetchall()
        self.assertEqual(len(avatar_rows), 2)
        self.assertEqual(avatar_rows[0], ("FAC-0105", "Faculty 105", "DOCENT", "Infectious Diseases"))
        self.assertEqual(avatar_rows[1], ("ORD-0042", "Resident 42", "ORDINATOR", "Epidemiology"))

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
