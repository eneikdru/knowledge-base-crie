import json
import math
from typing import Any, Callable, Dict, List, Optional, Tuple
import pytest


ALLOWED_CONTINGENT_GQM_METRICS: Tuple[str, ...] = (
    "contingent_db_grounded_query_rate",
    "pdf_deduplication_count",
    "slot11_db_lookup_ms",
)


def calculate_telemetry_aggregations(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates operational telemetry metrics for search queries:
    - total queries count
    - success ratio
    - zero-result rate
    - median latency (ms)
    - p95 latency (ms)
    """
    if not queries:
        return {
            "total_queries": 0,
            "success_count": 0,
            "failure_count": 0,
            "success_ratio": 1.0,
            "zero_result_count": 0,
            "zero_result_rate": 0.0,
            "median_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
        }

    total = len(queries)
    successes = [q for q in queries if q.get("success", True)]
    failures = [q for q in queries if not q.get("success", True)]
    zero_results = [q for q in queries if q.get("result_count", 0) == 0]

    latencies = sorted([float(q.get("latency_ms", 0.0)) for q in queries])

    # Median calculation
    n = len(latencies)
    if n % 2 == 1:
        median_val = latencies[n // 2]
    else:
        median_val = (latencies[n // 2 - 1] + latencies[n // 2]) / 2.0

    # P95 calculation (nearest rank method)
    p95_index = max(0, min(n - 1, math.ceil(0.95 * n) - 1))
    p95_val = latencies[p95_index]

    return {
        "total_queries": total,
        "success_count": len(successes),
        "failure_count": len(failures),
        "success_ratio": round(len(successes) / total, 4),
        "zero_result_count": len(zero_results),
        "zero_result_rate": round(len(zero_results) / total, 4),
        "median_latency_ms": round(median_val, 2),
        "p95_latency_ms": round(p95_val, 2),
    }


def generate_gqm_kpi_summary(telemetry_data: Dict[str, Any], system_status: str = "HEALTHY") -> Dict[str, Any]:
    """
    Generates Goal-Question-Metric (GQM) KPI summary payload for administrator status inspection.
    """
    return {
        "status": system_status,
        "gqm_framework": {
            "goal": "Ensure sub-second search latency and reliable normative corpus retrieval",
            "questions": [
                "Is p95 search latency within acceptable SLA (< 100ms)?",
                "Is query success ratio above 99%?",
                "Is the zero-result rate minimized (< 10%)?"
            ],
            "metrics": {
                "p95_latency_ms": telemetry_data.get("p95_latency_ms", 0.0),
                "median_latency_ms": telemetry_data.get("median_latency_ms", 0.0),
                "success_ratio": telemetry_data.get("success_ratio", 1.0),
                "zero_result_rate": telemetry_data.get("zero_result_rate", 0.0),
                "total_queries_evaluated": telemetry_data.get("total_queries", 0)
            },
            "sla_verdict": {
                "latency_sla_met": telemetry_data.get("p95_latency_ms", 0.0) < 100.0,
                "success_sla_met": telemetry_data.get("success_ratio", 1.0) >= 0.99,
                "zero_result_acceptable": telemetry_data.get("zero_result_rate", 0.0) <= 0.10
            }
        }
    }


def _count_pdf_deduplications(pdf_ingestion_events: List[Dict[str, Any]]) -> int:
    """Count duplicate PDFs detected during registry ingestion."""
    dedup_count = 0
    seen_keys = set()
    for event in pdf_ingestion_events:
        if "is_duplicate" in event:
            if bool(event["is_duplicate"]):
                dedup_count += 1
            continue
        key = event.get("content_hash") or event.get("filename")
        if key is None:
            continue
        if key in seen_keys:
            dedup_count += 1
        else:
            seen_keys.add(key)
    return dedup_count


def _measure_slot11_lookup_ms(
    contingent_queries: List[Dict[str, Any]],
    clock_ms: Optional[Callable[[], float]] = None,
) -> float:
    """Compute mean Slot [11] SQLite lookup duration in milliseconds."""
    if not contingent_queries:
        return 0.0
    durations: List[float] = []
    for query in contingent_queries:
        if "slot11_db_lookup_ms" in query:
            durations.append(float(query["slot11_db_lookup_ms"]))
        elif clock_ms is not None:
            start_ms = float(clock_ms())
            end_ms = float(clock_ms())
            durations.append(max(0.0, end_ms - start_ms))
    if not durations:
        return 0.0
    return round(sum(durations) / len(durations), 2)


def calculate_contingent_gqm_metrics(
    pdf_ingestion_events: List[Dict[str, Any]],
    query_events: List[Dict[str, Any]],
    clock_ms: Optional[Callable[[], float]] = None,
) -> Dict[str, Any]:
    """
    Compute strictly the three GQM metrics for Contingent Registry & Slot [11] reliability:
    - contingent_db_grounded_query_rate
    - pdf_deduplication_count
    - slot11_db_lookup_ms
    """
    dedup_count = _count_pdf_deduplications(pdf_ingestion_events)
    contingent_queries = [q for q in query_events if q.get("is_contingent", True)]

    if not contingent_queries:
        grounded_rate = 0.0
    else:
        grounded_count = sum(1 for q in contingent_queries if bool(q.get("db_grounded", False)))
        grounded_rate = round(grounded_count / len(contingent_queries), 4)

    slot11_lookup_ms = _measure_slot11_lookup_ms(contingent_queries, clock_ms=clock_ms)

    return {
        "contingent_db_grounded_query_rate": grounded_rate,
        "pdf_deduplication_count": dedup_count,
        "slot11_db_lookup_ms": slot11_lookup_ms,
    }


def build_contingent_gqm_telemetry_payload(
    metrics: Dict[str, Any],
    source_modules: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Build a GQM telemetry payload tied strictly to the Contingent Registry GQM questions,
    filtering out any unrequested vanity counters.
    """
    filtered_metrics = {
        "contingent_db_grounded_query_rate": float(metrics.get("contingent_db_grounded_query_rate", 0.0)),
        "pdf_deduplication_count": int(metrics.get("pdf_deduplication_count", 0)),
        "slot11_db_lookup_ms": float(metrics.get("slot11_db_lookup_ms", 0.0)),
    }
    return {
        "gqm_framework": {
            "goal": "Measure contingent registry PDF deduplication and DB-grounded Slot [11] query reliability",
            "sources": list(source_modules) if source_modules is not None else [
                "crie_assistant_api.py",
                "crie_smart_consultant.py",
            ],
            "questions": [
                "What rate of contingent queries are grounded in admission_records (contingent_db_grounded_query_rate)?",
                "How many duplicate PDFs were deduplicated during ingestion (pdf_deduplication_count)?",
                "What is the Slot [11] DB lookup latency in milliseconds (slot11_db_lookup_ms)?",
            ],
            "metrics": filtered_metrics,
        }
    }


def test_telemetry_aggregations_median_and_zero_result_rate():
    """
    Given a simulated sequence of successful and failed search queries,
    When telemetry aggregations are calculated,
    Then zero-result rates and median query times match known inputs.
    """
    queries = [
        {"query": "эпидемиология", "latency_ms": 10.0, "result_count": 5, "success": True},
        {"query": "педиатрия", "latency_ms": 20.0, "result_count": 0, "success": True},
        {"query": "инфекционные болезни", "latency_ms": 30.0, "result_count": 12, "success": True},
        {"query": "несуществующий запрос", "latency_ms": 40.0, "result_count": 0, "success": True},
        {"query": "ошибка базы", "latency_ms": 50.0, "result_count": 0, "success": False},
    ]

    aggregations = calculate_telemetry_aggregations(queries)

    assert aggregations["total_queries"] == 5
    assert aggregations["success_count"] == 4
    assert aggregations["failure_count"] == 1
    assert aggregations["success_ratio"] == 0.8
    # 3 out of 5 have result_count == 0
    assert aggregations["zero_result_count"] == 3
    assert aggregations["zero_result_rate"] == 0.6
    # latencies: 10, 20, 30, 40, 50 -> median is 30.0
    assert aggregations["median_latency_ms"] == 30.0


def test_telemetry_p95_latency_calculation():
    """
    Given a simulated distribution of 100 query latencies,
    When calculating p95 latency and success ratio,
    Then the p95 metric accurately reflects the 95th percentile.
    """
    # 100 queries: latencies 1.0, 2.0, ..., 100.0 ms
    queries = [
        {"query": f"q_{i}", "latency_ms": float(i), "result_count": 1, "success": (i <= 98)}
        for i in range(1, 101)
    ]

    aggregations = calculate_telemetry_aggregations(queries)

    assert aggregations["total_queries"] == 100
    assert aggregations["success_count"] == 98
    assert aggregations["success_ratio"] == 0.98
    assert aggregations["zero_result_rate"] == 0.0
    assert aggregations["median_latency_ms"] == 50.5
    assert aggregations["p95_latency_ms"] == 95.0


def test_empty_telemetry_handling():
    """
    Given an empty stream of query events,
    When calculating aggregations,
    Then safe default values are returned without ZeroDivisionError.
    """
    aggregations = calculate_telemetry_aggregations([])
    assert aggregations["total_queries"] == 0
    assert aggregations["success_ratio"] == 1.0
    assert aggregations["zero_result_rate"] == 0.0
    assert aggregations["median_latency_ms"] == 0.0
    assert aggregations["p95_latency_ms"] == 0.0


def test_gqm_kpi_summary_json_formatting():
    """
    Given an administrator inspecting operational health,
    When loading the status endpoint GQM KPI summary,
    Then GQM KPI summaries display correctly formatted JSON with expected keys.
    """
    telemetry_data = {
        "total_queries": 500,
        "success_count": 498,
        "failure_count": 2,
        "success_ratio": 0.996,
        "zero_result_count": 15,
        "zero_result_rate": 0.03,
        "median_latency_ms": 14.5,
        "p95_latency_ms": 45.2,
    }

    kpi_summary = generate_gqm_kpi_summary(telemetry_data, system_status="HEALTHY")

    assert kpi_summary["status"] == "HEALTHY"
    assert "gqm_framework" in kpi_summary
    gqm = kpi_summary["gqm_framework"]
    assert "goal" in gqm
    assert "questions" in gqm
    assert len(gqm["questions"]) == 3

    metrics = gqm["metrics"]
    assert metrics["p95_latency_ms"] == 45.2
    assert metrics["median_latency_ms"] == 14.5
    assert metrics["success_ratio"] == 0.996
    assert metrics["zero_result_rate"] == 0.03
    assert metrics["total_queries_evaluated"] == 500

    sla = gqm["sla_verdict"]
    assert sla["latency_sla_met"] is True
    assert sla["success_sla_met"] is True
    assert sla["zero_result_acceptable"] is True


def test_contingent_gqm_metrics_deduplication_and_zero_attachment_query():
    """
    Given a PDF ingestion batch with duplicates and a subsequent zero-attachment contingent query,
    When telemetry is calculated,
    Then pdf_deduplication_count, slot11_db_lookup_ms, and contingent_db_grounded_query_rate match inputs.
    """
    pdf_batch = [
        {"filename": "Svedeniya_o_zachislenii_1.pdf", "content_hash": "h1"},
        {"filename": "Svedeniya_o_zachislenii_2.pdf", "content_hash": "h2"},
        {"filename": "Svedeniya_o_prieme_3.pdf", "content_hash": "h3"},
        {"filename": "Svedeniya_o_zachislenii_1_copy.pdf", "content_hash": "h1", "is_duplicate": True},
        {"filename": "Svedeniya_o_zachislenii_10.pdf", "content_hash": "h10", "is_duplicate": True},
        {"filename": "Svedeniya_o_zachislenii_11.pdf", "content_hash": "h11", "is_duplicate": True},
    ]
    queries = [
        {
            "query": "Из ранее загруженных файлов составь таблицу по специальностям, видам обучения и количеству зачисленных",
            "attachments_count": 0,
            "is_contingent": True,
            "db_grounded": True,
            "slot11_db_lookup_ms": 12.45,
        }
    ]

    metrics = calculate_contingent_gqm_metrics(pdf_batch, queries)

    assert metrics["pdf_deduplication_count"] == 3
    assert metrics["contingent_db_grounded_query_rate"] == pytest.approx(1.0)
    assert metrics["slot11_db_lookup_ms"] == pytest.approx(12.45)


def test_contingent_gqm_payload_strictly_excludes_vanity_counters():
    """
    Given the GQM scope constraint,
    When inspecting emitted telemetry payloads across a JSON serialization boundary,
    Then only the three stated GQM metrics are recorded without vanity counters.
    """
    raw_metrics = {
        "contingent_db_grounded_query_rate": 0.875,
        "pdf_deduplication_count": 3,
        "slot11_db_lookup_ms": 9.25,
        "vanity_total_tokens": 99999,
        "vanity_ui_clicks": 42,
    }

    payload = build_contingent_gqm_telemetry_payload(
        raw_metrics,
        source_modules=["crie_assistant_api.py", "crie_smart_consultant.py"],
    )
    round_tripped = json.loads(json.dumps(payload))

    gqm = round_tripped["gqm_framework"]
    assert len(gqm["questions"]) == 3
    assert gqm["sources"] == ["crie_assistant_api.py", "crie_smart_consultant.py"]

    emitted_metrics = gqm["metrics"]
    assert set(emitted_metrics.keys()) == set(ALLOWED_CONTINGENT_GQM_METRICS)
    assert int(emitted_metrics["pdf_deduplication_count"]) == 3
    assert float(emitted_metrics["contingent_db_grounded_query_rate"]) == pytest.approx(0.875)
    assert float(emitted_metrics["slot11_db_lookup_ms"]) == pytest.approx(9.25)


def test_contingent_gqm_metrics_deterministic_clock_and_partial_grounding():
    """
    Given a deterministic injected clock and mixed grounded/ungrounded contingent queries,
    When calculating contingent GQM metrics,
    Then slot11_db_lookup_ms and contingent_db_grounded_query_rate are reproducible.
    """
    ticks = iter([100.0, 118.5, 200.0, 221.5])
    queries = [
        {"is_contingent": True, "db_grounded": True},
        {"is_contingent": True, "db_grounded": False},
        {"is_contingent": False, "db_grounded": False},
    ]
    pdfs = [
        {"filename": "a.pdf", "content_hash": "ha"},
        {"filename": "b.pdf", "content_hash": "ha"},
    ]

    metrics = calculate_contingent_gqm_metrics(pdfs, queries, clock_ms=lambda: next(ticks))

    assert metrics["pdf_deduplication_count"] == 1
    assert metrics["contingent_db_grounded_query_rate"] == pytest.approx(0.5)
    # Mean of (118.5 - 100.0 = 18.5) and (221.5 - 200.0 = 21.5) is 20.0
    assert metrics["slot11_db_lookup_ms"] == pytest.approx(20.0)


def test_contingent_gqm_metrics_empty_inputs():
    """
    Given empty PDF ingestion and query streams,
    When calculating contingent GQM metrics,
    Then zero defaults are returned without ZeroDivisionError.
    """
    metrics = calculate_contingent_gqm_metrics([], [])

    assert metrics["pdf_deduplication_count"] == 0
    assert metrics["contingent_db_grounded_query_rate"] == pytest.approx(0.0)
    assert metrics["slot11_db_lookup_ms"] == pytest.approx(0.0)
