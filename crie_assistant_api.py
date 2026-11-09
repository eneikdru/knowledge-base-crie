import time
import threading
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    event_type: str = Field(..., description="Type of telemetry event, e.g., 'search', 'click', 'document_view'")
    query_hash: Optional[str] = Field(None, description="Anonymized one-way hash or sanitized token of query")
    latency_ms: Optional[float] = Field(None, ge=0.0, description="Measured search/request latency in ms")
    click_rank: Optional[int] = Field(None, ge=0, description="Rank index of clicked result (0-based or 1-based)")
    results_count: Optional[int] = Field(None, ge=0, description="Number of items returned for search")
    session_token: Optional[str] = Field(None, description="Pseudonymous or anonymized session identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Non-PII metadata")


class TelemetryAggregator:
    """
    Thread-safe, zero-PII in-memory metric collector and aggregator.
    Tracks search latency, click-through ranks, zero-result queries, and document views.
    """
    def __init__(self, max_event_buffer: int = 10000):
        self._lock = threading.Lock()
        self._max_event_buffer = max_event_buffer
        self.reset()

    def reset(self):
        with self._lock:
            self._total_events: int = 0
            self._search_count: int = 0
            self._zero_result_count: int = 0
            self._total_latency_ms: float = 0.0
            self._min_latency_ms: float = float('inf')
            self._max_latency_ms: float = 0.0
            self._click_ranks: List[int] = []
            self._document_views: int = 0
            self._event_types: Dict[str, int] = {}

    def record(self, event: TelemetryEvent) -> None:
        # Ensure zero identifiable personal information (PII filter)
        clean_metadata = {}
        forbidden_pii_keys = {"fio", "name", "email", "phone", "passport", "ip", "address", "user_id"}
        if event.metadata:
            for k, v in event.metadata.items():
                if k.lower() not in forbidden_pii_keys:
                    clean_metadata[k] = v

        with self._lock:
            self._total_events += 1
            ev_type = event.event_type.lower()
            self._event_types[ev_type] = self._event_types.get(ev_type, 0) + 1

            if ev_type == "search":
                self._search_count += 1
                if event.latency_ms is not None:
                    lat = float(event.latency_ms)
                    self._total_latency_ms += lat
                    if lat < self._min_latency_ms:
                        self._min_latency_ms = lat
                    if lat > self._max_latency_ms:
                        self._max_latency_ms = lat
                if event.results_count is not None and event.results_count == 0:
                    self._zero_result_count += 1

            elif ev_type == "click":
                if event.click_rank is not None:
                    if len(self._click_ranks) < self._max_event_buffer:
                        self._click_ranks.append(event.click_rank)

            elif ev_type == "document_view":
                self._document_views += 1

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            avg_latency = (
                (self._total_latency_ms / self._search_count)
                if self._search_count > 0
                else 0.0
            )
            min_latency = self._min_latency_ms if self._search_count > 0 else 0.0
            avg_click_rank = (
                (sum(self._click_ranks) / len(self._click_ranks))
                if self._click_ranks
                else 0.0
            )
            zero_result_rate = (
                (self._zero_result_count / self._search_count)
                if self._search_count > 0
                else 0.0
            )
            return {
                "total_events": self._total_events,
                "search_count": self._search_count,
                "zero_result_count": self._zero_result_count,
                "zero_result_rate": round(zero_result_rate, 4),
                "document_views": self._document_views,
                "latency": {
                    "avg_ms": round(avg_latency, 2),
                    "min_ms": round(min_latency, 2),
                    "max_ms": round(self._max_latency_ms, 2)
                },
                "clicks": {
                    "total_clicks": len(self._click_ranks),
                    "avg_rank": round(avg_click_rank, 2)
                },
                "event_distribution": dict(self._event_types)
            }


telemetry_aggregator = TelemetryAggregator()
app = FastAPI(
    title="CRIE Assistant API",
    description="Lightweight knowledge base and assistant service for CRIE with privacy-preserving telemetry.",
    version="1.0.0"
)


@app.get("/")
def root():
    return {"status": "ok", "service": "crie-assistant-api"}


@app.post("/telemetry/event", status_code=202)
def record_telemetry_event(event: TelemetryEvent):
    """
    Fast in-memory ingestion endpoint recording search metrics without PII.
    Executes well under 5ms latency impact.
    """
    telemetry_aggregator.record(event)
    return {"status": "recorded", "event_type": event.event_type}


@app.get("/telemetry/metrics")
def get_telemetry_metrics():
    """
    Retrieves aggregated GQM operational metrics (search latency, click ranks, zero results).
    """
    return telemetry_aggregator.get_summary()


@app.post("/telemetry/reset")
def reset_telemetry_metrics():
    telemetry_aggregator.reset()
    return {"status": "reset_complete"}
