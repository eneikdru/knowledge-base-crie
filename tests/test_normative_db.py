import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from storage.normative_db import (
    get_connection,
    initialize_schema,
    ingest_catalog_data,
    search_normative_documents,
    explain_search_query_plan,
    DEFAULT_DB_PATH
)


class TestNormativeDocumentIndexing(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.test_dir.name) / "test_normative.db"
        
        self.sample_catalog = Path(self.test_dir.name) / "sample_catalog.json"
        catalog_content = {
            "total_normative_files": 4,
            "categories": [
                {
                    "category": "05 ООП РПД 2026_27",
                    "file_count": 2,
                    "files": [
                        {
                            "file_name": "ОХОП Образовательная программа ПЕДИАТРИЯ.docx",
                            "relative_path": "ООП 310819 Педиатрия/ОХОП.docx",
                            "extension": ".docx",
                            "size_bytes": 83470
                        },
                        {
                            "file_name": "Положение ФБУН ЦНИИ Эпидемиологии.docx",
                            "relative_path": "ФБУН/Положение.docx",
                            "extension": ".docx",
                            "size_bytes": 15420
                        }
                    ]
                },
                {
                    "category": "05 ООП ФОС",
                    "file_count": 2,
                    "files": [
                        {
                            "file_name": "БИЛЕТЫ ГИА инф. бол. 25.docx",
                            "relative_path": "ГИА/БИЛЕТЫ ГИА.docx",
                            "extension": ".docx",
                            "size_bytes": 39563
                        },
                        {
                            "file_name": "Протокол заседания ГЭК Педиатрия.docx",
                            "relative_path": "ГЭК/Протокол ГЭК.docx",
                            "extension": ".docx",
                            "size_bytes": 24100
                        }
                    ]
                }
            ]
        }
        with open(self.sample_catalog, "w", encoding="utf-8") as f:
            json.dump(catalog_content, f, ensure_ascii=False)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_schema_creation_and_foreign_keys(self):
        conn = get_connection(self.db_path)
        initialize_schema(conn)
        
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('categories', 'normative_documents')")
        tables = {row["name"] for row in cursor.fetchall()}
        self.assertIn("categories", tables)
        self.assertIn("normative_documents", tables)
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='normative_documents_fts'")
        fts_table = cursor.fetchone()
        self.assertIsNotNone(fts_table)
        conn.close()

    def test_ingestion_and_foreign_key_population(self):
        stats = ingest_catalog_data(self.sample_catalog, self.db_path)
        self.assertEqual(stats["categories_count"], 2)
        self.assertEqual(stats["documents_count"], 4)
        
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as c FROM categories")
        self.assertEqual(cursor.fetchone()["c"], 2)
        
        cursor.execute("SELECT COUNT(*) as c FROM normative_documents")
        self.assertEqual(cursor.fetchone()["c"], 4)
        
        cursor.execute("""
            SELECT doc.file_name, c.name as category_name
            FROM normative_documents doc
            JOIN categories c ON c.id = doc.category_id
        """)
        joined_rows = cursor.fetchall()
        self.assertEqual(len(joined_rows), 4)
        conn.close()

    def test_medical_abbreviations_query_speed_and_accuracy(self):
        ingest_catalog_data(self.sample_catalog, self.db_path)
        
        for acronym in ["ФБУН", "ГЭК", "ГИА"]:
            res = search_normative_documents(acronym, self.db_path)
            self.assertGreater(res["count"], 0, f"Expected results for {acronym}")
            self.assertLess(res["duration_ms"], 50.0, f"Query {acronym} took {res['duration_ms']}ms (> 50ms threshold)")
            
            first_match = res["results"][0]
            self.assertTrue(
                acronym.lower() in first_match["file_name"].lower() or 
                acronym.lower() in first_match["keywords"].lower() or
                acronym.lower() in first_match["match_snippet"].lower()
            )

    def test_query_plan_uses_fts_index(self):
        ingest_catalog_data(self.sample_catalog, self.db_path)
        plan = explain_search_query_plan("ГИА", self.db_path)
        plan_str = " ".join(plan)
        self.assertTrue(
            "normative_documents_fts" in plan_str or "VIRTUAL TABLE" in plan_str,
            f"Expected query plan to use FTS index, got: {plan_str}"
        )

    def test_production_corpus_catalog_if_available(self):
        prod_catalog = Path("data/normative/corpus_catalog.json")
        if prod_catalog.exists():
            stats = ingest_catalog_data(prod_catalog, self.db_path)
            self.assertGreater(stats["categories_count"], 0)
            self.assertGreater(stats["documents_count"], 0)
            
            for term in ["ГИА", "Педиатрия", "Эпидемиология"]:
                t0 = time.perf_counter()
                res = search_normative_documents(term, self.db_path)
                duration_ms = (time.perf_counter() - t0) * 1000.0
                self.assertLess(duration_ms, 50.0, f"Search {term} took {duration_ms}ms")


if __name__ == "__main__":
    unittest.main()
