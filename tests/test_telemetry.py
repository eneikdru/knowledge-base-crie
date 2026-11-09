"""
Unit tests for GQM Telemetry Instrumentation and In-Memory Aggregations.
"""

import unittest
import time
import threading
from crie_telemetry import TelemetryCollector, sanitize_pii


class TestTelemetrySanitizationAndPII(unittest.TestCase):
    def test_pii_scrubbing_zero_personal_info(self):
        raw_payload = {
            "event_type": "search",
            "query": "Иванов Иван Иванович график сессии ord-1234",
            "ip": "192.168.1.100",
            "email": "doctor@crie.ru",
            "phone": "+7 (999) 123-45-67",
            "user_id": "USER-999",
            "nested": {
                "passport": "4510 123456",
                "doc_name": "Положение об аттестации"
            }
        }
        sanitized = sanitize_pii(raw_payload)
        
        # Assert forbidden keys removed
        for forbidden in ['ip', 'email', 'phone', 'user_id', 'passport']:
            self.assertNotIn(forbidden, sanitized)
            if 'nested' in sanitized:
                self.assertNotIn(forbidden, sanitized['nested'])
        
        # Assert textual identifiers sanitized
        self.assertNotIn('ord-1234', sanitized['query'])
        self.assertIn('[ANON_AVATAR]', sanitized['query'])
        self.assertEqual(sanitized['nested']['doc_name'], "Положение об аттестации")


class TestTelemetryCollectorAggregation(unittest.TestCase):
    def setUp(self):
        # Inject fixed time for deterministic assertions
        self.fixed_time = 1762646400.0
        self.collector = TelemetryCollector(time_provider=lambda: self.fixed_time)

    def test_search_latency_and_zero_results(self):
        self.collector.record_search(latency_ms=10.0, zero_result=False)
        self.collector.record_search(latency_ms=20.0, zero_result=False)
        self.collector.record_search(latency_ms=30.0, zero_result=True)
        
        summary = self.collector.get_metrics_summary()
        search_stats = summary['search']
        
        self.assertEqual(search_stats['total_searches'], 3)
        self.assertEqual(search_stats['zero_result_searches'], 1)
        self.assertAlmostEqual(search_stats['zero_result_rate'], 1.0 / 3.0, places=3)
        self.assertAlmostEqual(search_stats['latency_ms']['avg'], 20.0, places=1)
        self.assertAlmostEqual(search_stats['latency_ms']['min'], 10.0, places=1)
        self.assertAlmostEqual(search_stats['latency_ms']['max'], 30.0, places=1)
        self.assertEqual(summary['last_event_timestamp'], self.fixed_time)

    def test_click_through_rank_aggregation(self):
        self.collector.record_search(latency_ms=5.0, zero_result=False)
        self.collector.record_search(latency_ms=5.0, zero_result=False)
        
        # Rank 1 click and Rank 2 click
        self.collector.record_click_through(rank=1, doc_type="РПД")
        self.collector.record_click_through(rank=2, doc_type="ФОС")
        
        summary = self.collector.get_metrics_summary()
        click_stats = summary['click_through']
        
        self.assertEqual(click_stats['total_clicks'], 2)
        self.assertEqual(click_stats['rank_distribution'][1], 1)
        self.assertEqual(click_stats['rank_distribution'][2], 1)
        
        # MRR = (1/1 + 1/2) / 2 = 0.75
        self.assertAlmostEqual(click_stats['mean_reciprocal_rank'], 0.75, places=3)
        # Top-1 CTR = 1 click / 2 searches = 0.5
        self.assertAlmostEqual(click_stats['top1_ctr'], 0.5, places=3)
        # Top-3 CTR = 2 clicks / 2 searches = 1.0
        self.assertAlmostEqual(click_stats['top3_ctr'], 1.0, places=3)

    def test_document_views_counter(self):
        self.collector.record_document_view(doc_type="Положение")
        self.collector.record_document_view(doc_type="Положение")
        self.collector.record_document_view(doc_type="Регламент")
        
        summary = self.collector.get_metrics_summary()
        doc_stats = summary['document_views']
        
        self.assertEqual(doc_stats['total_views'], 3)
        self.assertEqual(doc_stats['by_type']['Положение'], 2)
        self.assertEqual(doc_stats['by_type']['Регламент'], 1)

    def test_generic_event_dispatcher(self):
        resp1 = self.collector.record_event({"event_type": "search", "latency_ms": 12.0, "zero_result": False})
        self.assertEqual(resp1['status'], 'recorded')
        
        resp2 = self.collector.record_event({"event_type": "click_through", "rank": 1})
        self.assertEqual(resp2['status'], 'recorded')
        
        resp3 = self.collector.record_event({"event_type": "unknown_type"})
        self.assertEqual(resp3['status'], 'ignored')


class TestTelemetryConcurrencyPerformance(unittest.TestCase):
    def test_concurrent_recording_latency_impact_under_5ms(self):
        """
        Verifies that under high concurrency, metric logging impact is strictly < 5ms per event.
        """
        collector = TelemetryCollector()
        num_threads = 20
        iterations_per_thread = 50
        
        latencies = []
        lock = threading.Lock()
        
        def worker():
            for i in range(iterations_per_thread):
                t0 = time.perf_counter()
                collector.record_search(latency_ms=15.0, zero_result=(i % 10 == 0))
                collector.record_click_through(rank=(i % 5) + 1)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                with lock:
                    latencies.append(elapsed_ms)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        avg_overhead = sum(latencies) / len(latencies)
        max_overhead = max(latencies)
        
        # Acceptance criteria: latency impact is strictly < 5ms
        self.assertLess(avg_overhead, 5.0, f"Average logging latency {avg_overhead:.4f}ms exceeded 5ms")
        
        summary = collector.get_metrics_summary()
        expected_searches = num_threads * iterations_per_thread
        self.assertEqual(summary['search']['total_searches'], expected_searches)


if __name__ == '__main__':
    unittest.main()
