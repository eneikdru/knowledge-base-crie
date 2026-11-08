import time
from collections import deque
from typing import Dict, Any, List, Optional
import threading

class TelemetryCollector:
    """
    In-memory, thread-safe GQM event collector for search latency,
    click-through ranks, and zero-result queries with zero PII retention.
    """
    def __init__(self, max_events: int = 10000):
        self._lock = threading.Lock()
        self._max_events = max_events
        self._search_events: deque = deque(maxlen=max_events)
        self._click_events: deque = deque(maxlen=max_events)
        self._zero_result_queries_count: int = 0
        self._total_searches: int = 0
        self._total_search_latency_ms: float = 0.0

    def record_search(self, latency_ms: float, result_count: int, query_length: Optional[int] = None) -> None:
        # Ensure zero identifiable personal information (PII) is captured
        start_ts = time.time()
        with self._lock:
            self._total_searches += 1
            self._total_search_latency_ms += latency_ms
            is_zero_result = (result_count == 0)
            if is_zero_result:
                self._zero_result_queries_count += 1
            self._search_events.append({
                "timestamp": start_ts,
                "latency_ms": float(latency_ms),
                "result_count": int(result_count),
                "query_length": int(query_length) if query_length is not None else 0,
                "is_zero_result": is_zero_result
            })

    def record_click(self, rank: int, document_id: Optional[str] = None) -> None:
        # document_id is scrubbed or hashed if needed; rank is pure numeric rank (1-based or 0-based)
        with self._lock:
            self._click_events.append({
                "timestamp": time.time(),
                "rank": int(rank),
                "has_doc": bool(document_id)
            })

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            avg_latency = (
                (self._total_search_latency_ms / self._total_searches)
                if self._total_searches > 0 else 0.0
            )
            clicks = list(self._click_events)
            ranks = [c["rank"] for c in clicks]
            avg_rank = (sum(ranks) / len(ranks)) if ranks else 0.0

            return {
                "total_searches": self._total_searches,
                "average_search_latency_ms": round(avg_latency, 2),
                "zero_result_queries_count": self._zero_result_queries_count,
                "total_clicks": len(clicks),
                "average_click_rank": round(avg_rank, 2)
            }

    def reset(self) -> None:
        with self._lock:
            self._search_events.clear()
            self._click_events.clear()
            self._zero_result_queries_count = 0
            self._total_searches = 0
            self._total_search_latency_ms = 0.0

global_telemetry = TelemetryCollector()
