"""
CRIE Assistant API Service.
FastAPI service providing Knowledge Base search, AI Assistant consultation,
Order drafting, Faculty workload calculation, and zero-PII telemetry.
"""

import re
import time
import threading
from collections import defaultdict, deque
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


class TelemetrySearchEvent(BaseModel):
    query_hash: Optional[str] = Field(None, description="Anonymized hash of query or sanitized keyword token")
    query_length: int = Field(..., ge=0, description="Character length of query without raw text")
    latency_ms: float = Field(..., ge=0.0, description="Search duration in milliseconds")
    result_count: int = Field(..., ge=0, description="Number of results returned")
    specialty_filter: Optional[str] = Field(None, description="Specialty filter used")
    doc_type_filter: Optional[str] = Field(None, description="Document type filter used")


class TelemetryClickEvent(BaseModel):
    rank: int = Field(..., ge=1, description="Rank position clicked by user (1-indexed)")
    doc_id: str = Field(..., description="Anonymized document or catalog ID")
    query_length: Optional[int] = Field(None, ge=0, description="Length of query associated with click")


class TelemetryCollector:
    """
    Thread-safe, lightweight, in-memory telemetry collector for GQM metrics.
    Ensures sub-millisecond record time (<5ms overhead constraint) and zero PII storage.
    """
    def __init__(self, max_samples: int = 10000):
        self._lock = threading.Lock()
        self._max_samples = max_samples
        self._search_latencies = deque(maxlen=max_samples)
        self._total_searches = 0
        self._zero_result_searches = 0
        self._click_ranks = deque(maxlen=max_samples)
        self._total_clicks = 0
        self._filter_counts = defaultdict(int)

    def record_search(self, event: TelemetrySearchEvent) -> None:
        with self._lock:
            self._total_searches += 1
            self._search_latencies.append(event.latency_ms)
            if event.result_count == 0:
                self._zero_result_searches += 1
            if event.specialty_filter:
                # Sanitize
                clean_spec = re.sub(r'[^a-zA-Z0-9_.-]', '', event.specialty_filter)
                self._filter_counts[f"spec:{clean_spec}"] += 1
            if event.doc_type_filter:
                clean_type = re.sub(r'[^a-zA-Z0-9_.-]', '', event.doc_type_filter)
                self._filter_counts[f"type:{clean_type}"] += 1

    def record_click(self, event: TelemetryClickEvent) -> None:
        with self._lock:
            self._total_clicks += 1
            self._click_ranks.append(event.rank)

    def get_metrics_summary(self) -> Dict[str, Any]:
        with self._lock:
            count = len(self._search_latencies)
            if count > 0:
                sorted_latencies = sorted(self._search_latencies)
                p50 = sorted_latencies[int(count * 0.50)]
                p95 = sorted_latencies[min(int(count * 0.95), count - 1)]
                avg_lat = round(sum(sorted_latencies) / count, 2)
            else:
                p50, p95, avg_lat = 0.0, 0.0, 0.0

            click_count = len(self._click_ranks)
            avg_rank = round(sum(self._click_ranks) / click_count, 2) if click_count > 0 else 0.0
            zero_result_rate = round((self._zero_result_searches / self._total_searches), 4) if self._total_searches > 0 else 0.0
            ctr = round((self._total_clicks / self._total_searches), 4) if self._total_searches > 0 else 0.0

            return {
                "total_searches": self._total_searches,
                "zero_result_searches": self._zero_result_searches,
                "zero_result_rate": zero_result_rate,
                "search_latency_p50_ms": p50,
                "search_latency_p95_ms": p95,
                "search_latency_avg_ms": avg_lat,
                "total_clicks": self._total_clicks,
                "click_through_rate": ctr,
                "avg_click_rank": avg_rank,
                "filter_usage": dict(self._filter_counts)
            }

    def reset(self) -> None:
        with self._lock:
            self._search_latencies.clear()
            self._click_ranks.clear()
            self._total_searches = 0
            self._zero_result_searches = 0
            self._total_clicks = 0
            self._filter_counts.clear()


telemetry_collector = TelemetryCollector()

app = FastAPI(
    title="CRIE Assistant API",
    description="Backend API for Knowledge Base, AI Assistant, and Workload calculations with zero-PII GQM telemetry.",
    version="1.0.0"
)


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": time.time()}


@app.post("/api/telemetry/search")
def track_search_metric(event: TelemetrySearchEvent):
    """
    Record telemetry for a search execution. No raw search text or PII is recorded.
    """
    start = time.perf_counter()
    telemetry_collector.record_search(event)
    duration_ms = (time.perf_counter() - start) * 1000.0
    return {"recorded": True, "duration_ms": round(duration_ms, 3)}


@app.post("/api/telemetry/click")
def track_click_metric(event: TelemetryClickEvent):
    """
    Record telemetry for a document/item click with ranking information.
    """
    telemetry_collector.record_click(event)
    return {"recorded": True}


@app.get("/api/telemetry/stats")
def get_telemetry_stats():
    """
    Get aggregated search latency, click ranks, and zero-result rates.
    """
    return telemetry_collector.get_metrics_summary()
