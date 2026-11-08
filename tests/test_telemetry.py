import time
import pytest
from fastapi.testclient import TestClient
from crie_assistant_api import app
from telemetry_collector import global_telemetry, TelemetryCollector

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_metrics():
    global_telemetry.reset()
    yield
    global_telemetry.reset()

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_search_ping_and_zero_result_aggregation():
    # Ping normal search
    r1 = client.post("/api/v1/telemetry/search-ping", json={"latency_ms": 42.5, "result_count": 10, "query_length": 7})
    assert r1.status_code == 202

    # Ping zero-result search
    r2 = client.post("/api/v1/telemetry/search-ping", json={"latency_ms": 12.0, "result_count": 0, "query_length": 15})
    assert r2.status_code == 202

    metrics_resp = client.get("/api/v1/telemetry/metrics")
    assert metrics_resp.status_code == 200
    data = metrics_resp.json()
    assert data["total_searches"] == 2
    assert data["zero_result_queries_count"] == 1
    assert data["average_search_latency_ms"] == round((42.5 + 12.0) / 2, 2)

def test_click_rank_aggregation():
    client.post("/api/v1/telemetry/click-ping", json={"rank": 1})
    client.post("/api/v1/telemetry/click-ping", json={"rank": 3})

    metrics_resp = client.get("/api/v1/telemetry/metrics")
    assert metrics_resp.status_code == 200
    data = metrics_resp.json()
    assert data["total_clicks"] == 2
    assert data["average_click_rank"] == 2.0

def test_telemetry_latency_under_5ms():
    collector = TelemetryCollector()
    latencies = []
    for i in range(100):
        t0 = time.perf_counter()
        collector.record_search(latency_ms=15.0, result_count=5, query_length=10)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0) # ms

    max_latency = max(latencies)
    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 1.0, f"Average collector latency should be < 1ms, got {avg_latency}ms"
    assert max_latency < 5.0, f"Max collector latency should be < 5ms, got {max_latency}ms"

def test_zero_pii_preserved():
    collector = TelemetryCollector()
    collector.record_search(latency_ms=20.0, result_count=0, query_length=5)
    collector.record_click(rank=2, document_id="anon_token_123")

    summary = collector.get_summary()
    # Summary keys must only contain aggregated counts/averages
    for key in summary.keys():
        assert "email" not in key.lower()
        assert "user" not in key.lower()
        assert "query_text" not in key.lower()
        assert "ip" not in key.lower()
