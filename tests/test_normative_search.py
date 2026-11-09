import json
import os
import time
import unittest
from normative_search_index import (
    InvertedIndex,
    stem_word,
    tokenize,
    extract_specialties,
    detect_document_type,
    get_normative_index
)


class TestNormativeSearchIndex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "normative", "corpus_catalog.json"
        )
        cls.index = InvertedIndex()
        cls.loaded_count = cls.index.load_from_catalog(cls.catalog_path)

    def test_catalog_load_count(self):
        self.assertEqual(self.loaded_count, 1697)
        self.assertEqual(self.index.total_docs, 1697)
        self.assertTrue(self.index.is_loaded)

    def test_specialty_extraction(self):
        text1 = "ООП 310819 Педиатрия РПД 1 Педиатрия.docx"
        text2 = "ООП 320812 Эпидемиология"
        self.assertIn("31.08.19", extract_specialties(text1))
        self.assertIn("32.08.12", extract_specialties(text2))

    def test_stemming_and_tokenization(self):
        tokens = tokenize("Рабочая программа детских инфекций РПД")
        self.assertIn("рабочая", tokens)
        self.assertIn("программа", tokens)
        self.assertIn("рпд", tokens)
        self.assertEqual(stem_word("педиатрия"), "педиатр")
        self.assertEqual(stem_word("эпидемиология"), "эпидемиолог")

    def test_sub_10ms_latency_single_query(self):
        queries = [
            "РПД",
            "ГИА",
            "ГЭК",
            "УМС",
            "Педиатрия",
            "Инфекционные болезни",
            "Эпидемиология",
            "31.08.19",
            "Лабораторная диагностика"
        ]
        for q in queries:
            res = self.index.search(q, limit=20)
            self.assertLess(res["query_time_ms"], 10.0, f"Query '{q}' took {res['query_time_ms']}ms, expected < 10ms")
            self.assertGreater(res["total"], 0, f"Query '{q}' returned no results")

    def test_abbreviation_expansion_rpd(self):
        res = self.index.search("РПД", limit=10)
        self.assertGreater(res["total"], 0)
        first_hit = res["results"][0]
        self.assertTrue("рпд" in first_hit["file_name"].lower() or "программа" in first_hit["file_name"].lower())

    def test_abbreviation_expansion_gia(self):
        res = self.index.search("ГИА", limit=10)
        self.assertGreater(res["total"], 0)
        # Verify snippet highlighting
        snippets = [hit["snippet"] for hit in res["results"]]
        self.assertTrue(any("<mark>" in s for s in snippets))

    def test_faceted_filtering_by_specialty(self):
        res = self.index.search("", specialty="31.08.19", limit=50)
        self.assertGreater(res["total"], 0)
        for doc in res["results"]:
            self.assertIn("31.08.19", doc["specialties"])

    def test_faceted_filtering_by_doc_type(self):
        res = self.index.search("", doc_type="ФОС", limit=50)
        self.assertGreater(res["total"], 0)
        for doc in res["results"]:
            self.assertEqual(doc["doc_type"], "ФОС")

    def test_get_normative_index_singleton(self):
        idx = get_normative_index(self.catalog_path)
        self.assertTrue(idx.is_loaded)
        self.assertEqual(idx.total_docs, 1697)


if __name__ == "__main__":
    unittest.main()
