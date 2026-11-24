import json
import math
from typing import Dict, List, Any, Sequence
import pytest


CONTINGENT_GQM_ALLOWED_METRICS = (
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


def calculate_contingent_gqm_metrics(events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes only the GQM-scoped contingent registry telemetry metrics:
    - contingent_db_grounded_query_rate
    - pdf_deduplication_count
    - slot11_db_lookup_ms
    """
    contingent_queries = [e for e in events if e.get("is_contingent_query", False)]
    dedup_total = sum(max(0, int(e.get("pdf_deduplication_count", 0))) for e in events)

    if not contingent_queries:
        return {
            "contingent_db_grounded_query_rate": 0.0,
            "pdf_deduplication_count": dedup_total,
            "slot11_db_lookup_ms": 0.0,
        }

    grounded_count = sum(1 for q in contingent_queries if q.get("db_grounded", False))
    lookup_latencies = [max(0.0, float(q.get("slot11_db_lookup_ms", 0.0))) for q in contingent_queries]

    return {
        "contingent_db_grounded_query_rate": round(grounded_count / len(contingent_queries), 4),
        "pdf_deduplication_count": dedup_total,
        "slot11_db_lookup_ms": round(sum(lookup_latencies) / len(lookup_latencies), 2),
    }


def generate_contingent_gqm_payload(events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Builds the GQM telemetry payload tied strictly to the stated contingent registry GQM questions.
    """
    metrics = calculate_contingent_gqm_metrics(events)
    return {
        "gqm_framework": {
            "goal": (
                "Ensure contingent registry queries are reliably grounded in persistent DB records "
                "with deduplicated PDF ingestion and fast slot [11] lookup"
            ),
            "questions": [
                {
                    "id": "Q1",
                    "question": "What proportion of contingent queries are grounded in persistent admission_records?",
                    "metric": "contingent_db_grounded_query_rate",
                },
                {
                    "id": "Q2",
                    "question": "How many duplicate PDF files were deduplicated during ingestion?",
                    "metric": "pdf_deduplication_count",
                },
                {
                    "id": "Q3",
                    "question": "What is the slot [11] persistent DB lookup latency in milliseconds?",
                    "metric": "slot11_db_lookup_ms",
                },
            ],
            "metrics": metrics,
        }
    }


def record_contingent_gqm_telemetry_batch(
    pdf_batch_keys: Sequence[str],
    contingent_queries: Sequence[Dict[str, Any]],
    slot11_lookup_latencies_ms: Sequence[float],
) -> Dict[str, Any]:
    """
    Deterministic simulation helper for a PDF ingestion batch with duplicates followed by
    zero-attachment contingent queries using injected slot [11] DB lookup timings.
    """
    if len(contingent_queries) != len(slot11_lookup_latencies_ms):
        raise ValueError("slot11_lookup_latencies_ms must match contingent_queries length")

    seen_keys = set()
    duplicate_count = 0
    for key in pdf_batch_keys:
        if key in seen_keys:
            duplicate_count += 1
        else:
            seen_keys.add(key)

    events: List[Dict[str, Any]] = [{"pdf_deduplication_count": duplicate_count}]
    for query, lookup_ms in zip(contingent_queries, slot11_lookup_latencies_ms):
        events.append({
            "is_contingent_query": True,
            "has_attachments": bool(query.get("has_attachments", False)),
            "db_grounded": bool(query.get("db_grounded", False)),
            "slot11_db_lookup_ms": float(lookup_ms),
        })

    return generate_contingent_gqm_payload(events)


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


def test_contingent_gqm_pdf_dedup_and_zero_attachment_query():
    """
    Given a PDF ingestion batch with duplicates and a subsequent zero-attachment contingent query,
    When contingent GQM telemetry is recorded,
    Then pdf_deduplication_count, slot11_db_lookup_ms, and contingent_db_grounded_query_rate reflect exact inputs.
    """
    pdf_batch_keys = [
        "Svedeniya_o_zachislenii_ordinatura_2026",
        "Svedeniya_o_zachislenii_ordinatura_2026",  # duplicate [1]
        "Svedeniya_o_prieme_ordinatura_2026",
        "Svedeniya_o_zachislenii_aspirantura_2026",
        "Svedeniya_o_prieme_aspirantura_2026",
        "Svedeniya_o_zachislenii_celevaya_2026",
        "Svedeniya_o_zachislenii_dogovor_2026",
        "Svedeniya_o_prieme_celevaya_2026",
        "Svedeniya_o_prieme_dogovor_2026",
        "Svedeniya_o_zachislenii_ordinatura_2026",  # duplicate [10]
        "Svedeniya_o_prieme_ordinatura_2026",       # duplicate [11]
    ]
    queries = [
        {"has_attachments": False, "db_grounded": True},
    ]
    payload = record_contingent_gqm_telemetry_batch(
        pdf_batch_keys=pdf_batch_keys,
        contingent_queries=queries,
        slot11_lookup_latencies_ms=[12.4],
    )

    metrics = payload["gqm_framework"]["metrics"]
    assert metrics["pdf_deduplication_count"] == 3
    assert math.isclose(float(metrics["contingent_db_grounded_query_rate"]), 1.0, rel_tol=1e-6)
    assert math.isclose(float(metrics["slot11_db_lookup_ms"]), 12.4, rel_tol=1e-6)


def test_contingent_gqm_scope_has_no_vanity_counters():
    """
    Given the GQM scope constraint,
    When inspecting emitted contingent telemetry payloads,
    Then no unrequested vanity counters are recorded outside the stated GQM questions.
    """
    payload = generate_contingent_gqm_payload([
        {"pdf_deduplication_count": 2},
        {"is_contingent_query": True, "db_grounded": True, "slot11_db_lookup_ms": 8.5},
    ])

    gqm = payload["gqm_framework"]
    question_metrics = {q["metric"] for q in gqm["questions"]}
    emitted_metric_keys = set(gqm["metrics"].keys())

    assert question_metrics == set(CONTINGENT_GQM_ALLOWED_METRICS)
    assert emitted_metric_keys == set(CONTINGENT_GQM_ALLOWED_METRICS)


def test_contingent_gqm_mixed_grounding_and_empty_events():
    """
    Given mixed grounded and ungrounded contingent queries or an empty event list,
    When calculating contingent GQM metrics,
    Then grounding rate and average slot [11] lookup latency compute safely without ZeroDivisionError.
    """
    empty_metrics = calculate_contingent_gqm_metrics([])
    assert empty_metrics["pdf_deduplication_count"] == 0
    assert math.isclose(float(empty_metrics["contingent_db_grounded_query_rate"]), 0.0, abs_tol=1e-9)
    assert math.isclose(float(empty_metrics["slot11_db_lookup_ms"]), 0.0, abs_tol=1e-9)

    mixed_metrics = calculate_contingent_gqm_metrics([
        {"pdf_deduplication_count": 1},
        {"is_contingent_query": True, "db_grounded": True, "slot11_db_lookup_ms": 10.0},
        {"is_contingent_query": True, "db_grounded": False, "slot11_db_lookup_ms": 20.0},
        {"is_contingent_query": True, "db_grounded": True, "slot11_db_lookup_ms": 15.0},
    ])
    assert mixed_metrics["pdf_deduplication_count"] == 1
    assert mixed_metrics["contingent_db_grounded_query_rate"] == pytest.approx(0.6667, abs=1e-4)
    assert mixed_metrics["slot11_db_lookup_ms"] == pytest.approx(15.0, abs=1e-4)


def test_contingent_gqm_json_roundtrip_type_safe_comparison():
    """
    Given a serialized contingent GQM telemetry payload,
    When parsed back from JSON,
    Then numeric comparisons remain type-safe across the JSON serialization boundary.
    """
    payload = record_contingent_gqm_telemetry_batch(
        pdf_batch_keys=["doc_a", "doc_a", "doc_b"],
        contingent_queries=[
            {"has_attachments": False, "db_grounded": True},
            {"has_attachments": False, "db_grounded": True},
        ],
        slot11_lookup_latencies_ms=[7.25, 11.75],
    )

    decoded = json.loads(json.dumps(payload))
    metrics = decoded["gqm_framework"]["metrics"]

    assert int(metrics["pdf_deduplication_count"]) == 1
    assert float(metrics["contingent_db_grounded_query_rate"]) == pytest.approx(1.0, abs=1e-6)
    assert float(metrics["slot11_db_lookup_ms"]) == pytest.approx(9.5, abs=1e-6)
