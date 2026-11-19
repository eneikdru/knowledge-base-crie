import json
import math
from typing import Dict, List, Any, Optional
import pytest


CONTINGENT_GQM_METRIC_KEYS = frozenset(
    {
        "contingent_db_grounded_query_rate",
        "pdf_deduplication_count",
        "slot11_db_lookup_ms",
    }
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


def calculate_contingent_gqm_metrics(
    ingestion_batches: List[Dict[str, Any]],
    contingent_queries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Computes strictly scoped GQM metrics for contingent PDF registry ingestion and
    Slot [11] DB-grounded zero-attachment queries:
    - contingent_db_grounded_query_rate
    - pdf_deduplication_count
    - slot11_db_lookup_ms
    """
    dedup_count = sum(int(batch.get("duplicates_skipped", 0)) for batch in ingestion_batches)

    zero_attachment_queries = [
        q for q in contingent_queries if int(q.get("attachment_count", 0)) == 0
    ]
    if not zero_attachment_queries:
        grounded_rate = 0.0
        avg_lookup_ms = 0.0
    else:
        grounded = [
            q for q in zero_attachment_queries if bool(q.get("db_grounded", False))
        ]
        grounded_rate = round(len(grounded) / len(zero_attachment_queries), 4)
        lookup_latencies = [
            float(q.get("slot11_db_lookup_ms", 0.0)) for q in zero_attachment_queries
        ]
        avg_lookup_ms = round(sum(lookup_latencies) / len(lookup_latencies), 2)

    return {
        "contingent_db_grounded_query_rate": grounded_rate,
        "pdf_deduplication_count": dedup_count,
        "slot11_db_lookup_ms": avg_lookup_ms,
    }


def generate_contingent_gqm_payload(
    ingestion_batches: List[Dict[str, Any]],
    contingent_queries: List[Dict[str, Any]],
    source_component: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Builds the GQM telemetry payload tied strictly to the three contingent-registry
    GQM questions without emitting unrequested vanity counters.
    """
    metrics = calculate_contingent_gqm_metrics(ingestion_batches, contingent_queries)
    payload: Dict[str, Any] = {
        "goal": "Measure contingent PDF deduplication and DB-grounded Slot [11] query reliability",
        "questions": [
            "What fraction of zero-attachment contingent queries are grounded in admission_records?",
            "How many duplicate PDFs were deduplicated during registry ingestion?",
            "What is the Slot [11] SQLite lookup latency in milliseconds?",
        ],
        "metrics": metrics,
    }
    if source_component:
        payload["component"] = source_component
    return payload


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


def test_contingent_gqm_metrics_with_pdf_duplicates_and_zero_attachment_query():
    """
    Given a PDF ingestion batch with duplicates and a subsequent zero-attachment contingent query,
    When processed for GQM telemetry,
    Then telemetry records pdf_deduplication_count, slot11_db_lookup_ms, and
    contingent_db_grounded_query_rate with no unrequested vanity counters.
    """
    ingestion_batches = [
        {"total_files": 11, "unique_files": 8, "duplicates_skipped": 3}
    ]
    contingent_queries = [
        {
            "query": "Из ранее загруженных файлов составь таблицу по специальностям, видам обучения и количеству зачисленных",
            "attachment_count": 0,
            "db_grounded": True,
            "slot11_db_lookup_ms": 12.4,
        },
        {
            "query": "Покажи зачисленных по целевой квоте",
            "attachment_count": 0,
            "db_grounded": True,
            "slot11_db_lookup_ms": 15.6,
        },
    ]

    payload = generate_contingent_gqm_payload(
        ingestion_batches,
        contingent_queries,
        source_component="crie_assistant_api.py",
    )
    serialized = json.loads(json.dumps(payload))

    assert len(serialized["questions"]) == 3
    assert set(serialized["metrics"].keys()) == CONTINGENT_GQM_METRIC_KEYS
    assert int(serialized["metrics"]["pdf_deduplication_count"]) == 3
    assert float(serialized["metrics"]["contingent_db_grounded_query_rate"]) == pytest.approx(1.0)
    assert float(serialized["metrics"]["slot11_db_lookup_ms"]) == pytest.approx(14.0)


def test_contingent_gqm_metrics_partial_grounding_and_empty_inputs():
    """
    Given mixed grounded/ungrounded zero-attachment queries or empty inputs,
    When calculating contingent GQM metrics,
    Then rates reflect only zero-attachment queries and empty inputs return safe zeros.
    """
    empty_metrics = calculate_contingent_gqm_metrics([], [])
    assert set(empty_metrics.keys()) == CONTINGENT_GQM_METRIC_KEYS
    assert empty_metrics["pdf_deduplication_count"] == 0
    assert empty_metrics["contingent_db_grounded_query_rate"] == pytest.approx(0.0)
    assert empty_metrics["slot11_db_lookup_ms"] == pytest.approx(0.0)

    queries = [
        {"attachment_count": 0, "db_grounded": True, "slot11_db_lookup_ms": 8.0},
        {"attachment_count": 0, "db_grounded": False, "slot11_db_lookup_ms": 12.0},
        {"attachment_count": 1, "db_grounded": False, "slot11_db_lookup_ms": 99.0},
    ]
    metrics = calculate_contingent_gqm_metrics([{"duplicates_skipped": 2}], queries)
    assert set(metrics.keys()) == CONTINGENT_GQM_METRIC_KEYS
    assert metrics["pdf_deduplication_count"] == 2
    assert metrics["contingent_db_grounded_query_rate"] == pytest.approx(0.5)
    assert metrics["slot11_db_lookup_ms"] == pytest.approx(10.0)
