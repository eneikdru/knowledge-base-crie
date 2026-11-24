import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import pytest


VALID_CONTINGENT_EVENT_TYPES = frozenset({"ingestion", "query"})


def ensure_contingent_gqm_schema(conn: sqlite3.Connection) -> None:
    """Initialize the contingent_gqm_events SQLite table and index idempotently."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS contingent_gqm_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            order_doc_id TEXT,
            parsed_row_count INTEGER NOT NULL DEFAULT 0,
            failed_row_count INTEGER NOT NULL DEFAULT 0,
            sql_backed INTEGER NOT NULL DEFAULT 0,
            citation_present INTEGER NOT NULL DEFAULT 0,
            latency_ms REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_contingent_gqm_events_type_created
        ON contingent_gqm_events (event_type, created_at)
        """
    )
    conn.commit()


def record_contingent_gqm_event(
    conn: sqlite3.Connection,
    event_type: str,
    order_doc_id: Optional[str] = None,
    parsed_row_count: int = 0,
    failed_row_count: int = 0,
    sql_backed: bool = False,
    citation_present: bool = False,
    latency_ms: float = 0.0,
    created_at: Optional[str] = None,
    clock: Optional[Callable[[], str]] = None,
) -> int:
    """Persist a single GQM ingestion or query telemetry event in SQLite."""
    if event_type not in VALID_CONTINGENT_EVENT_TYPES:
        raise ValueError(f"Unsupported event_type: {event_type!r}")
    if parsed_row_count < 0 or failed_row_count < 0:
        raise ValueError("Row counts must be non-negative")
    if latency_ms < 0.0:
        raise ValueError("latency_ms must be non-negative")

    ensure_contingent_gqm_schema(conn)
    timestamp = created_at
    if timestamp is None:
        timestamp = (
            clock()
            if clock is not None
            else datetime.now(timezone.utc).isoformat()
        )

    cursor = conn.execute(
        """
        INSERT INTO contingent_gqm_events (
            event_type,
            order_doc_id,
            parsed_row_count,
            failed_row_count,
            sql_backed,
            citation_present,
            latency_ms,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_type,
            order_doc_id,
            int(parsed_row_count),
            int(failed_row_count),
            1 if sql_backed else 0,
            1 if citation_present else 0,
            float(latency_ms),
            timestamp,
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_contingent_gqm_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Compute Q1 completeness rate, Q2 SQL-grounded citation rate, and Q3 failure count
    directly from the contingent_gqm_events SQLite table without scanning external logs.
    """
    ensure_contingent_gqm_schema(conn)
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_events,
            COALESCE(SUM(CASE WHEN event_type = 'ingestion' THEN 1 ELSE 0 END), 0) AS ingestion_events,
            COALESCE(SUM(CASE WHEN event_type = 'query' THEN 1 ELSE 0 END), 0) AS query_events,
            COALESCE(SUM(CASE WHEN event_type = 'ingestion' THEN parsed_row_count ELSE 0 END), 0) AS parsed_row_count,
            COALESCE(SUM(failed_row_count), 0) AS total_failed_rows,
            COALESCE(SUM(CASE WHEN event_type = 'ingestion' THEN failed_row_count ELSE 0 END), 0) AS ingestion_failed_rows,
            COALESCE(SUM(CASE WHEN event_type = 'query' AND sql_backed = 1 AND citation_present = 1 THEN 1 ELSE 0 END), 0) AS sql_grounded_citation_count,
            COALESCE(AVG(latency_ms), 0.0) AS avg_latency_ms
        FROM contingent_gqm_events
        """
    ).fetchone()

    total_events = int(row[0])
    ingestion_events = int(row[1])
    query_events = int(row[2])
    parsed_row_count = int(row[3])
    total_failed_rows = int(row[4])
    ingestion_failed_rows = int(row[5])
    sql_grounded_citation_count = int(row[6])
    avg_latency_ms = float(row[7])

    total_ingestion_rows = parsed_row_count + ingestion_failed_rows
    q1_completeness_rate = (
        round(parsed_row_count / total_ingestion_rows, 4)
        if total_ingestion_rows > 0
        else 0.0
    )
    q2_sql_grounded_citation_rate = (
        round(sql_grounded_citation_count / query_events, 4)
        if query_events > 0
        else 0.0
    )

    return {
        "total_events": total_events,
        "ingestion_events": ingestion_events,
        "query_events": query_events,
        "parsed_row_count": parsed_row_count,
        "failed_row_count": total_failed_rows,
        "sql_grounded_citation_count": sql_grounded_citation_count,
        "q1_completeness_rate": q1_completeness_rate,
        "q2_sql_grounded_citation_rate": q2_sql_grounded_citation_rate,
        "q3_failure_count": total_failed_rows,
        "avg_latency_ms": round(avg_latency_ms, 2),
    }


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


def test_contingent_gqm_schema_columns():
    """
    Given storage initialization runs,
    When inspecting contingent_gqm_events,
    Then all required telemetry columns exist.
    """
    conn = sqlite3.connect(":memory:")
    try:
        ensure_contingent_gqm_schema(conn)
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(contingent_gqm_events)").fetchall()
        }
        expected = {
            "event_type",
            "order_doc_id",
            "parsed_row_count",
            "failed_row_count",
            "sql_backed",
            "citation_present",
            "latency_ms",
            "created_at",
        }
        assert expected.issubset(columns)
    finally:
        conn.close()


def test_contingent_gqm_summary_zero_events():
    """
    Given zero recorded events on a fresh install,
    When get_contingent_gqm_summary runs,
    Then safe zeroed defaults are returned without ZeroDivisionError.
    """
    conn = sqlite3.connect(":memory:")
    try:
        ensure_contingent_gqm_schema(conn)
        summary = get_contingent_gqm_summary(conn)
        assert summary == {
            "total_events": 0,
            "ingestion_events": 0,
            "query_events": 0,
            "parsed_row_count": 0,
            "failed_row_count": 0,
            "sql_grounded_citation_count": 0,
            "q1_completeness_rate": 0.0,
            "q2_sql_grounded_citation_rate": 0.0,
            "q3_failure_count": 0,
            "avg_latency_ms": 0.0,
        }
    finally:
        conn.close()


def test_contingent_gqm_summary_persists_across_restarts(tmp_path: Path):
    """
    Given ingestion and query telemetry events are recorded,
    When the database connection is reopened across a restart,
    Then get_contingent_gqm_summary computes exact Q1, Q2, and Q3 metrics.
    """
    db_path = tmp_path / "contingent_gqm.db"
    fixed_clock = lambda: "2026-11-24T10:00:00+00:00"

    conn1 = sqlite3.connect(db_path)
    try:
        ensure_contingent_gqm_schema(conn1)
        record_contingent_gqm_event(
            conn1,
            event_type="ingestion",
            order_doc_id="doc-1",
            parsed_row_count=18,
            failed_row_count=2,
            latency_ms=40.0,
            clock=fixed_clock,
        )
        record_contingent_gqm_event(
            conn1,
            event_type="ingestion",
            order_doc_id="doc-2",
            parsed_row_count=10,
            failed_row_count=0,
            latency_ms=20.0,
            created_at="2026-11-24T10:01:00+00:00",
        )
        record_contingent_gqm_event(
            conn1,
            event_type="query",
            order_doc_id="doc-1",
            sql_backed=True,
            citation_present=True,
            latency_ms=15.0,
            clock=fixed_clock,
        )
        record_contingent_gqm_event(
            conn1,
            event_type="query",
            order_doc_id="doc-2",
            sql_backed=True,
            citation_present=False,
            latency_ms=25.0,
            clock=fixed_clock,
        )
        record_contingent_gqm_event(
            conn1,
            event_type="query",
            order_doc_id=None,
            failed_row_count=1,
            sql_backed=False,
            citation_present=False,
            latency_ms=50.0,
            clock=fixed_clock,
        )
    finally:
        conn1.close()

    conn2 = sqlite3.connect(db_path)
    try:
        summary = get_contingent_gqm_summary(conn2)
    finally:
        conn2.close()

    decoded = json.loads(json.dumps(summary))
    assert decoded["total_events"] == 5
    assert decoded["ingestion_events"] == 2
    assert decoded["query_events"] == 3
    assert decoded["parsed_row_count"] == 28
    assert decoded["failed_row_count"] == 3
    assert decoded["sql_grounded_citation_count"] == 1
    # Q1: 28 / (28 + 2) = 0.9333
    assert float(decoded["q1_completeness_rate"]) == pytest.approx(0.9333, abs=1e-4)
    # Q2: 1 / 3 = 0.3333
    assert float(decoded["q2_sql_grounded_citation_rate"]) == pytest.approx(0.3333, abs=1e-4)
    # Q3: 2 ingestion failed rows + 1 query failed row = 3
    assert decoded["q3_failure_count"] == 3
    assert float(decoded["avg_latency_ms"]) == pytest.approx(30.0, abs=1e-2)


def test_contingent_gqm_validation_rejects_invalid_inputs():
    """Verify invalid event types and negative counters are rejected."""
    conn = sqlite3.connect(":memory:")
    try:
        with pytest.raises(ValueError):
            record_contingent_gqm_event(conn, event_type="unknown")
        with pytest.raises(ValueError):
            record_contingent_gqm_event(conn, event_type="ingestion", parsed_row_count=-1)
        with pytest.raises(ValueError):
            record_contingent_gqm_event(conn, event_type="query", latency_ms=-0.5)
    finally:
        conn.close()
