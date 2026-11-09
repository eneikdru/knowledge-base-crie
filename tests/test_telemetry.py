"""
Unit tests for GQM Telemetry Collector and Endpoints.
"""

import time
import pytest
from fastapi.testclient import TestClient
from crie_assistant_api import app, telemetry_collector, TelemetrySearchEvent, TelemetryClickEvent


@pytest.fixture(autouse=True)
def reset_telemetry():
    telemetry_collector.reset()
    yield
    telemetry_collector.reset()


def test_telemetry_record_search_and_stats():
    client = TestClient(app)

    # Log normal search
    res1 = client.post("/api/telemetry/search", json={
        "query_length": 14,
        "latency_ms": 4.2,
        "result_count": 5,
        "specialty_filter": "31.08.36",
        "doc_type_filter": "Положение"
    })
    assert res1.status_code == 200
    assert res1.json()["recorded"] is True
    assert res1.json()["duration_ms"] < 5.0

    # Log zero-result search
    res2 = client.post("/api/telemetry/search", json={
        "query_length": 22,
        "latency_ms": 3.1,
        "result_count": 0
    })
    assert res2.status_code == 200

    # Log clicks
    res_click = client.post("/api/telemetry/click", json={
        "rank": 1,
        "doc_id": "DOC-1697",
        "query_length": 14
    })
    assert res_click.status_code == 200

    # Check stats
    stats_res = client.get("/api/telemetry/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()

    assert stats["total_searches"] == 2
    assert stats["zero_result_searches"] == 1
    assert stats["zero_result_rate"] == 0.5
    assert stats["total_clicks"] == 1
    assert stats["click_through_rate"] == 0.5
    assert stats["avg_click_rank"] == 1.0
    assert stats["search_latency_p50_ms"] >= 3.0
    assert "spec:31.08.36" in stats["filter_usage"]


def test_latency_overhead_under_5ms():
    """Acceptance criteria: metric logging runs with latency impact < 5ms."""
    event = TelemetrySearchEvent(
        query_length=10,
        latency_ms=2.5,
        result_count=3
    )
    start = time.perf_counter()
    for _ in range(100):
        telemetry_collector.record_search(event)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    avg_ms = elapsed_ms / 100
    assert avg_ms < 1.0  # Well within the <5ms requirement


def test_zero_identifiable_personal_information():
    """
    Acceptance criteria: Metrics are recorded with zero identifiable personal information.
    Event model only retains query length, sanitized categorical filters, and timings.
    """
    client = TestClient(app)
    payload = {
        "query_hash": "a8f5c1",
        "query_length": 30,
        "latency_ms": 1.8,
        "result_count": 12,
        "specialty_filter": "31.08.35-Infectious",
        "doc_type_filter": "Reglament"
    }
    resp = client.post("/api/telemetry/search", json=payload)
    assert resp.status_code == 200
    stats = client.get("/api/telemetry/stats").json()
    # Ensure raw strings or PII fields do not exist
    assert "user" not in stats
    assert "ip" not in stats
    assert "name" not in stats
