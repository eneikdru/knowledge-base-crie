import time
import pytest
from fastapi.testclient import TestClient
from crie_assistant_api import app, telemetry_aggregator, TelemetryEvent

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_collector():
    telemetry_aggregator.reset()
    yield
    telemetry_aggregator.reset()


def test_root_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_record_search_and_zero_result_event():
    # 1. Search with results
    res1 = client.post("/telemetry/event", json={
        "event_type": "search",
        "query_hash": "a8f5b3c2",
        "latency_ms": 12.5,
        "results_count": 5,
        "session_token": "ORD-1042"
    })
    assert res1.status_code == 202

    # 2. Zero-result search
    res2 = client.post("/telemetry/event", json={
        "event_type": "search",
        "query_hash": "c7e1d409",
        "latency_ms": 8.0,
        "results_count": 0,
        "session_token": "ORD-1042"
    })
    assert res2.status_code == 202

    # 3. Verify aggregated metrics
    metrics_res = client.get("/telemetry/metrics")
    assert metrics_res.status_code == 200
    data = metrics_res.json()

    assert data["total_events"] == 2
    assert data["search_count"] == 2
    assert data["zero_result_count"] == 1
    assert data["zero_result_rate"] == 0.5
    assert data["latency"]["avg_ms"] == 10.25
    assert data["latency"]["min_ms"] == 8.0
    assert data["latency"]["max_ms"] == 12.5


def test_click_through_rank_aggregation():
    client.post("/telemetry/event", json={"event_type": "click", "click_rank": 1})
    client.post("/telemetry/event", json={"event_type": "click", "click_rank": 3})
    client.post("/telemetry/event", json={"event_type": "document_view"})

    metrics = client.get("/telemetry/metrics").json()
    assert metrics["total_events"] == 3
    assert metrics["document_views"] == 1
    assert metrics["clicks"]["total_clicks"] == 2
    assert metrics["clicks"]["avg_rank"] == 2.0


def test_privacy_and_no_pii_storage():
    # Ingest event with attempted PII fields in metadata
    res = client.post("/telemetry/event", json={
        "event_type": "search",
        "query_hash": "hash123",
        "latency_ms": 4.2,
        "results_count": 10,
        "metadata": {
            "fio": "Иванов Иван Иванович",
            "passport": "4500 123456",
            "specialty_code": "31.08.36"
        }
    })
    assert res.status_code == 202
    metrics = client.get("/telemetry/metrics").json()
    # Ensure metrics do not leak metadata or PII
    metrics_str = str(metrics)
    assert "Иванов" not in metrics_str
    assert "4500" not in metrics_str


def test_concurrent_performance_overhead_sub_5ms():
    # Verify single ingestion call execution time is well under 5ms overhead
    payload = {
        "event_type": "search",
        "query_hash": "bench_query",
        "latency_ms": 15.0,
        "results_count": 3
    }
    start = time.perf_counter()
    iterations = 100
    for _ in range(iterations):
        res = client.post("/telemetry/event", json=payload)
        assert res.status_code == 202
    elapsed_total_ms = (time.perf_counter() - start) * 1000.0
    avg_ms = elapsed_total_ms / iterations
    # Acceptance criteria: API latency impacted by less than 5ms
    assert avg_ms < 5.0
