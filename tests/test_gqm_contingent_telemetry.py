"""Unit tests for GQM contingent registry and slot [11] telemetry contract."""

import hashlib
import json
import math
import sqlite3
import unittest
from typing import Callable, Dict, Iterable, List, Optional, Tuple

ALLOWED_GQM_METRICS = frozenset(
    {
        "contingent_db_grounded_query_rate",
        "pdf_deduplication_count",
        "slot11_db_lookup_ms",
    }
)


def init_contingent_schema(conn: sqlite3.Connection) -> None:
    """Create SQLite tables for uploaded PDF documents and admission records."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS uploaded_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            doc_type TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admission_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER NOT NULL,
            order_number TEXT NOT NULL,
            order_date TEXT NOT NULL,
            education_level TEXT NOT NULL,
            specialty_code TEXT NOT NULL,
            specialty_name TEXT NOT NULL,
            financing_type TEXT NOT NULL,
            admission_stage TEXT NOT NULL,
            enrolled_count INTEGER NOT NULL,
            student_identifiers_json TEXT NOT NULL,
            FOREIGN KEY (doc_id) REFERENCES uploaded_documents(id)
        )
        """
    )
    conn.commit()


class GqmContingentTelemetryRecorder:
    """Minimal GQM telemetry recorder scoped strictly to the three contingent metrics."""

    def __init__(self, clock_ms: Callable[[], float]) -> None:
        """Initialize recorder with an injectable millisecond clock."""
        self._clock_ms = clock_ms
        self.pdf_deduplication_count = 0
        self.slot11_db_lookup_ms = 0.0
        self._total_contingent_queries = 0
        self._db_grounded_queries = 0

    def ingest_pdf_batch(
        self,
        conn: sqlite3.Connection,
        documents: Iterable[Tuple[str, str, str, str, int]],
    ) -> int:
        """Ingest PDF payloads while deduplicating identical document contents."""
        existing_hashes = {
            hashlib.sha256(f"{row[0]}::{row[1]}".encode("utf-8")).hexdigest()
            for row in conn.execute("SELECT doc_type, raw_text FROM uploaded_documents")
        }
        inserted = 0
        for filename, uploaded_at, raw_text, doc_type, enrolled_count in documents:
            digest = hashlib.sha256(f"{doc_type}::{raw_text}".encode("utf-8")).hexdigest()
            if digest in existing_hashes:
                self.pdf_deduplication_count += 1
                continue
            existing_hashes.add(digest)
            cursor = conn.execute(
                "INSERT INTO uploaded_documents (filename, uploaded_at, raw_text, doc_type) VALUES (?, ?, ?, ?)",
                (filename, uploaded_at, raw_text, doc_type),
            )
            doc_id = cursor.lastrowid
            conn.execute(
                """
                INSERT INTO admission_records (
                    doc_id, order_number, order_date, education_level,
                    specialty_code, specialty_name, financing_type,
                    admission_stage, enrolled_count, student_identifiers_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    f"ORD-{doc_id}",
                    uploaded_at,
                    "ординатура",
                    "31.08.01",
                    "Акушерство и гинекология",
                    "бюджет",
                    "основной",
                    enrolled_count,
                    json.dumps([f"S-{doc_id}-{i}" for i in range(enrolled_count)]),
                ),
            )
            inserted += 1
        conn.commit()
        return inserted

    def run_slot11_contingent_query(
        self,
        conn: sqlite3.Connection,
        has_attachments: bool,
    ) -> List[Tuple[str, str, int]]:
        """Build slot [11] context from persistent DB records even with no attachments."""
        self._total_contingent_queries += 1
        start_ms = self._clock_ms()
        rows = conn.execute(
            """
            SELECT ar.specialty_name, ar.financing_type, SUM(ar.enrolled_count)
            FROM admission_records ar
            JOIN uploaded_documents ud ON ud.id = ar.doc_id
            GROUP BY ar.specialty_name, ar.financing_type
            """
        ).fetchall()
        end_ms = self._clock_ms()
        self.slot11_db_lookup_ms = max(0.0, float(end_ms - start_ms))
        if rows or not has_attachments:
            if rows:
                self._db_grounded_queries += 1
        return [(str(r[0]), str(r[1]), int(r[2])) for r in rows]

    def build_payload(
        self, extra_metrics: Optional[Dict[str, object]] = None
    ) -> str:
        """Serialize GQM telemetry payload while rejecting unrequested vanity metrics."""
        rate = (
            float(self._db_grounded_queries) / float(self._total_contingent_queries)
            if self._total_contingent_queries > 0
            else 0.0
        )
        payload: Dict[str, object] = {
            "contingent_db_grounded_query_rate": rate,
            "pdf_deduplication_count": self.pdf_deduplication_count,
            "slot11_db_lookup_ms": self.slot11_db_lookup_ms,
        }
        if extra_metrics:
            disallowed = set(extra_metrics.keys()) - ALLOWED_GQM_METRICS
            if disallowed:
                raise ValueError(f"Disallowed vanity metrics outside GQM scope: {sorted(disallowed)}")
            payload.update(extra_metrics)
        return json.dumps(payload, sort_keys=True)


class TestGqmContingentTelemetry(unittest.TestCase):
    """Verify GQM metric emission, determinism, and scope constraints."""

    def setUp(self) -> None:
        """Create an in-memory SQLite database with deterministic test clock."""
        self.conn = sqlite3.connect(":memory:")
        init_contingent_schema(self.conn)
        self._ticks = iter([100.0, 114.25, 200.0, 205.5])
        self.recorder = GqmContingentTelemetryRecorder(clock_ms=lambda: next(self._ticks))

    def tearDown(self) -> None:
        """Close in-memory SQLite connection."""
        self.conn.close()

    def test_deduplication_and_zero_attachment_slot11_telemetry(self) -> None:
        """Batch with duplicates plus zero-attachment query emits exact GQM metrics."""
        batch = [
            ("Svedeniya_o_zachislenii_1.pdf", "2026-08-10", "order-alpha", "zachislenie", 5),
            ("Svedeniya_o_zachislenii_1_dup.pdf", "2026-08-10", "order-alpha", "zachislenie", 5),
            ("Svedeniya_o_prieme_10.pdf", "2026-08-11", "order-beta", "priem", 3),
            ("Svedeniya_o_prieme_10_dup.pdf", "2026-08-11", "order-beta", "priem", 3),
            ("Svedeniya_o_prieme_11_dup.pdf", "2026-08-11", "order-beta", "priem", 3),
        ]
        inserted = self.recorder.ingest_pdf_batch(self.conn, batch)
        self.assertEqual(inserted, 2)

        aggregated = self.recorder.run_slot11_contingent_query(self.conn, has_attachments=False)
        self.assertEqual(aggregated, [("Акушерство и гинекология", "бюджет", 8)])

        raw_json = self.recorder.build_payload()
        parsed = json.loads(raw_json)

        self.assertEqual(set(parsed.keys()), ALLOWED_GQM_METRICS)
        self.assertEqual(parsed["pdf_deduplication_count"], 3)

        lookup_ms = parsed["slot11_db_lookup_ms"]
        self.assertIsInstance(lookup_ms, (int, float))
        self.assertTrue(math.isclose(float(lookup_ms), 14.25, rel_tol=1e-9, abs_tol=1e-9))

        grounded_rate = parsed["contingent_db_grounded_query_rate"]
        self.assertIsInstance(grounded_rate, (int, float))
        self.assertTrue(math.isclose(float(grounded_rate), 1.0, rel_tol=1e-9, abs_tol=1e-9))

    def test_gqm_scope_rejects_unrequested_vanity_counters(self) -> None:
        """Telemetry builder rejects metrics outside the stated GQM questions."""
        with self.assertRaises(ValueError):
            self.recorder.build_payload(extra_metrics={"vanity_token_count": 999})

        parsed = json.loads(self.recorder.build_payload())
        self.assertEqual(set(parsed.keys()), ALLOWED_GQM_METRICS)


if __name__ == "__main__":
    unittest.main()
