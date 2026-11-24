import logging
import math
import sqlite3
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import pytest


ALLOWED_REGISTRY_TABLES = frozenset({"enrolled_trainees", "pps_staff", "rup_curricula"})

GQM_LIFECYCLE_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS gqm_lifecycle_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL CHECK (question_id IN ('Q1', 'Q2', 'Q3')),
    event_type TEXT NOT NULL CHECK (event_type IN ('UPLOAD_DEDUPLICATION', 'REGISTRY_CORRECTION', 'UPLOAD_HELP_CHAT')),
    recorded_at TEXT NOT NULL,
    success INTEGER NOT NULL CHECK (success IN (0, 1)),
    deduplicated INTEGER CHECK (deduplicated IN (0, 1)),
    target_table TEXT CHECK (target_table IN ('enrolled_trainees', 'pps_staff', 'rup_curricula')),
    result_count INTEGER CHECK (result_count >= 0),
    latency_ms INTEGER NOT NULL DEFAULT 0 CHECK (latency_ms >= 0)
)
"""

INSERT_GQM_LIFECYCLE_EVENT_SQL = """
INSERT INTO gqm_lifecycle_events (
    question_id,
    event_type,
    recorded_at,
    success,
    deduplicated,
    target_table,
    result_count,
    latency_ms
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

GQM_EVENT_SPECS: Dict[str, Dict[str, Any]] = {
    "UPLOAD_DEDUPLICATION": {
        "question_id": "Q1",
        "column": "deduplicated",
    },
    "REGISTRY_CORRECTION": {
        "question_id": "Q2",
        "column": "target_table",
    },
    "UPLOAD_HELP_CHAT": {
        "question_id": "Q3",
        "column": "result_count",
    },
}


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_gqm_lifecycle_record(
    event_type: str,
    payload: Dict[str, Any],
    clock: Callable[[], str] = _utc_iso_now,
) -> Dict[str, Any]:
    """
    Projects an incoming lifecycle event strictly onto the Q1-Q3 schema fields with timestamp.
    Extra fields (raw file bytes, trainee FIO, chat prompts) are never retained.
    """
    spec = GQM_EVENT_SPECS.get(event_type)
    if spec is None:
        raise ValueError(f"Unsupported GQM lifecycle event_type: {event_type}")

    latency_ms = int(payload.get("latency_ms", 0))
    if latency_ms < 0:
        raise ValueError("latency_ms must be non-negative")

    deduplicated: Optional[int] = None
    target_table: Optional[str] = None
    result_count: Optional[int] = None

    if event_type == "UPLOAD_DEDUPLICATION":
        deduplicated = 1 if bool(payload.get("deduplicated", False)) else 0
    elif event_type == "REGISTRY_CORRECTION":
        candidate_table = payload.get("target_table")
        if candidate_table not in ALLOWED_REGISTRY_TABLES:
            raise ValueError(f"Unsupported registry target_table: {candidate_table}")
        target_table = candidate_table
    elif event_type == "UPLOAD_HELP_CHAT":
        count = int(payload.get("result_count", 0))
        if count < 0:
            raise ValueError("result_count must be non-negative")
        result_count = count

    return {
        "question_id": spec["question_id"],
        "event_type": event_type,
        "recorded_at": str(payload.get("recorded_at") or clock()),
        "success": 1 if bool(payload.get("success", True)) else 0,
        "deduplicated": deduplicated,
        "target_table": target_table,
        "result_count": result_count,
        "latency_ms": latency_ms,
    }


class SqliteGqmTelemetryRecorder:
    """
    Fail-open SQLite recorder for GQM Q1-Q3 document-lifecycle events.
    """

    def __init__(
        self,
        db_path: str,
        clock: Callable[[], str] = _utc_iso_now,
        logger: Optional[logging.Logger] = None,
        connection_factory: Optional[Callable[[str], sqlite3.Connection]] = None,
    ) -> None:
        self.db_path = db_path
        self.clock = clock
        self.logger = logger or logging.getLogger(__name__)
        self.connection_factory = connection_factory or sqlite3.connect

    def record_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """
        Writes a single Q1-Q3 lifecycle event to SQLite. Logs a non-fatal warning and returns
        False if projection or SQLite write fails, never raising to callers.
        """
        try:
            record = build_gqm_lifecycle_record(event_type, payload, clock=self.clock)
            conn = self.connection_factory(self.db_path)
            try:
                conn.execute(GQM_LIFECYCLE_TABLE_DDL)
                conn.execute(
                    INSERT_GQM_LIFECYCLE_EVENT_SQL,
                    (
                        record["question_id"],
                        record["event_type"],
                        record["recorded_at"],
                        record["success"],
                        record["deduplicated"],
                        record["target_table"],
                        record["result_count"],
                        record["latency_ms"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()
            return True
        except Exception as exc:
            self.logger.warning(
                "Non-fatal GQM telemetry write failure for %s: %s",
                event_type,
                exc,
            )
            return False

    def run_with_telemetry(
        self,
        primary_operation: Callable[[], Any],
        event_type: str,
        payload_builder: Callable[[Any], Dict[str, Any]],
    ) -> Any:
        """
        Runs an upload or registry edit and records GQM telemetry fail-open.
        """
        result = primary_operation()
        try:
            payload = payload_builder(result)
            self.record_event(event_type, payload)
        except Exception as exc:
            self.logger.warning(
                "Non-fatal GQM telemetry capture failure for %s: %s",
                event_type,
                exc,
            )
        return result


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


def test_gqm_sqlite_schema_and_q1_q3_strict_fields(tmp_path):
    """
    Given upload deduplication, registry correction, and upload-help chat events,
    When recorded in SQLite,
    Then only fields required for Q1, Q2, and Q3 are stored with timestamps.
    """
    db_path = str(tmp_path / "gqm_telemetry.db")
    fixed_clock = lambda: "2026-11-24T12:00:00Z"
    recorder = SqliteGqmTelemetryRecorder(db_path=db_path, clock=fixed_clock)

    assert recorder.record_event(
        "UPLOAD_DEDUPLICATION",
        {
            "deduplicated": True,
            "success": True,
            "latency_ms": 15,
            "raw_file_bytes": b"secret-content",
            "filename": "trainees.xlsx",
        },
    ) is True
    assert recorder.record_event(
        "REGISTRY_CORRECTION",
        {
            "target_table": "enrolled_trainees",
            "success": True,
            "latency_ms": 32,
            "fio": "Иванов Иван Иванович",
            "old_value": "budget",
        },
    ) is True
    assert recorder.record_event(
        "UPLOAD_HELP_CHAT",
        {
            "result_count": 4,
            "success": True,
            "latency_ms": 21,
            "chat_prompt": "Как загрузить РУП?",
        },
    ) is True

    conn = sqlite3.connect(db_path)
    try:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(gqm_lifecycle_events)").fetchall()]
        assert columns == [
            "id",
            "question_id",
            "event_type",
            "recorded_at",
            "success",
            "deduplicated",
            "target_table",
            "result_count",
            "latency_ms",
        ]
        rows = conn.execute(
            "SELECT question_id, event_type, recorded_at, success, deduplicated, target_table, result_count, latency_ms "
            "FROM gqm_lifecycle_events ORDER BY id ASC"
        ).fetchall()
    finally:
        conn.close()

    assert rows == [
        ("Q1", "UPLOAD_DEDUPLICATION", "2026-11-24T12:00:00Z", 1, 1, None, None, 15),
        ("Q2", "REGISTRY_CORRECTION", "2026-11-24T12:00:00Z", 1, None, "enrolled_trainees", None, 32),
        ("Q3", "UPLOAD_HELP_CHAT", "2026-11-24T12:00:00Z", 1, None, None, 4, 21),
    ]


def test_gqm_recorder_rejects_invalid_event_fail_open(tmp_path, caplog):
    """
    Given an unsupported event type or registry table,
    When recorded through the fail-open recorder,
    Then it logs a non-fatal warning and returns False without raising.
    """
    db_path = str(tmp_path / "gqm_invalid.db")
    recorder = SqliteGqmTelemetryRecorder(db_path=db_path, clock=lambda: "2026-11-24T12:00:00Z")

    with caplog.at_level(logging.WARNING):
        assert recorder.record_event(
            "REGISTRY_CORRECTION",
            {"target_table": "unknown_table", "success": True, "latency_ms": 5},
        ) is False
        assert recorder.record_event("UNKNOWN_EVENT", {"success": True}) is False

    assert any("Non-fatal GQM telemetry write failure" in rec.message for rec in caplog.records)


def test_gqm_recorder_fail_open_on_simulated_write_failure(tmp_path, caplog):
    """
    Given a simulated SQLite telemetry write failure,
    When an upload or record edit occurs,
    Then the primary operation still succeeds and logs a non-fatal warning.
    """
    def failing_connection(_db_path: str) -> sqlite3.Connection:
        raise sqlite3.OperationalError("database is locked")

    recorder = SqliteGqmTelemetryRecorder(
        db_path=str(tmp_path / "locked.db"),
        clock=lambda: "2026-11-24T12:00:00Z",
        connection_factory=failing_connection,
    )

    with caplog.at_level(logging.WARNING):
        upload_result = recorder.run_with_telemetry(
            lambda: {"document_id": 5, "deduplicated": True},
            "UPLOAD_DEDUPLICATION",
            lambda res: {"deduplicated": res["deduplicated"], "success": True, "latency_ms": 11},
        )
        edit_result = recorder.run_with_telemetry(
            lambda: {"record_id": 12, "table": "pps_staff", "updated": True},
            "REGISTRY_CORRECTION",
            lambda res: {"target_table": res["table"], "success": True, "latency_ms": 19},
        )

    assert upload_result == {"document_id": 5, "deduplicated": True}
    assert edit_result == {"record_id": 12, "table": "pps_staff", "updated": True}
    warning_messages = [rec.message for rec in caplog.records if rec.levelno == logging.WARNING]
    assert len(warning_messages) == 2
    assert all("Non-fatal GQM telemetry write failure" in msg for msg in warning_messages)
