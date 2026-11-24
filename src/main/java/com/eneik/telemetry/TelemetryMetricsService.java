package com.eneik.telemetry;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Types;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;
import java.util.function.Supplier;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Aggregates search telemetry and records GQM Q1-Q3 document-lifecycle events fail-open to SQLite.
 */
public class TelemetryMetricsService {

    public static final String GQM_EVENTS_TABLE_DDL =
            "CREATE TABLE IF NOT EXISTS gqm_lifecycle_events ("
                    + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + "question_id TEXT NOT NULL CHECK (question_id IN ('Q1', 'Q2', 'Q3')), "
                    + "event_type TEXT NOT NULL CHECK (event_type IN ('UPLOAD_DEDUPLICATION', 'REGISTRY_CORRECTION', 'UPLOAD_HELP_CHAT')), "
                    + "recorded_at TEXT NOT NULL, "
                    + "success INTEGER NOT NULL CHECK (success IN (0, 1)), "
                    + "deduplicated INTEGER CHECK (deduplicated IN (0, 1)), "
                    + "target_table TEXT CHECK (target_table IN ('enrolled_trainees', 'pps_staff', 'rup_curricula')), "
                    + "result_count INTEGER CHECK (result_count >= 0), "
                    + "latency_ms INTEGER NOT NULL DEFAULT 0 CHECK (latency_ms >= 0)"
                    + ")";

    public static final String INSERT_GQM_EVENT_SQL =
            "INSERT INTO gqm_lifecycle_events "
                    + "(question_id, event_type, recorded_at, success, deduplicated, target_table, result_count, latency_ms) "
                    + "VALUES (?, ?, ?, ?, ?, ?, ?, ?)";

    /**
     * Storage abstraction for persisting GQM lifecycle events.
     */
    @FunctionalInterface
    public interface LifecycleEventStore {
        void save(TelemetryEvent event, Instant recordedAt) throws Exception;
    }

    /**
     * Supplier for JDBC connections, enabling testable SQLite connection injection.
     */
    @FunctionalInterface
    public interface ConnectionSupplier {
        Connection get() throws SQLException;
    }

    /**
     * SQLite-backed store writing strictly the Q1-Q3 lifecycle event fields and timestamp.
     */
    public static class JdbcSqliteEventStore implements LifecycleEventStore {
        private final ConnectionSupplier connectionSupplier;

        public JdbcSqliteEventStore(String jdbcUrl) {
            this(() -> DriverManager.getConnection(jdbcUrl));
        }

        public JdbcSqliteEventStore(ConnectionSupplier connectionSupplier) {
            this.connectionSupplier = Objects.requireNonNull(connectionSupplier, "connectionSupplier must not be null");
        }

        @Override
        public void save(TelemetryEvent event, Instant recordedAt) throws SQLException {
            if (event == null || event.getEventType() == null) {
                throw new IllegalArgumentException("GQM lifecycle eventType is required");
            }
            try (Connection connection = connectionSupplier.get()) {
                try (Statement schemaStmt = connection.createStatement()) {
                    schemaStmt.execute(GQM_EVENTS_TABLE_DDL);
                }
                try (PreparedStatement ps = connection.prepareStatement(INSERT_GQM_EVENT_SQL)) {
                    bindEventParameters(ps, event, recordedAt);
                    ps.executeUpdate();
                }
            }
        }

        private static void bindEventParameters(PreparedStatement ps, TelemetryEvent event, Instant recordedAt)
                throws SQLException {
            TelemetryEvent.LifecycleEventType type = event.getEventType();
            ps.setString(1, type.getQuestionId());
            ps.setString(2, type.name());
            ps.setString(3, recordedAt.toString());
            ps.setInt(4, event.isSuccess() ? 1 : 0);

            if (type == TelemetryEvent.LifecycleEventType.UPLOAD_DEDUPLICATION && event.getDeduplicated() != null) {
                ps.setInt(5, event.getDeduplicated() ? 1 : 0);
            } else {
                ps.setNull(5, Types.INTEGER);
            }

            if (type == TelemetryEvent.LifecycleEventType.REGISTRY_CORRECTION && event.getTargetTable() != null) {
                ps.setString(6, event.getTargetTable());
            } else {
                ps.setNull(6, Types.VARCHAR);
            }

            if (type == TelemetryEvent.LifecycleEventType.UPLOAD_HELP_CHAT
                    && event.getLifecycleResultCount() != null) {
                ps.setInt(7, event.getLifecycleResultCount());
            } else {
                ps.setNull(7, Types.INTEGER);
            }

            ps.setLong(8, Math.max(0L, event.getLatencyMs()));
        }
    }

    private final LifecycleEventStore eventStore;
    private final Clock clock;
    private final Logger logger;

    public TelemetryMetricsService() {
        this(null, Clock.systemUTC(), Logger.getLogger(TelemetryMetricsService.class.getName()));
    }

    public TelemetryMetricsService(String sqliteJdbcUrl) {
        this(new JdbcSqliteEventStore(sqliteJdbcUrl),
                Clock.systemUTC(),
                Logger.getLogger(TelemetryMetricsService.class.getName()));
    }

    public TelemetryMetricsService(LifecycleEventStore eventStore, Clock clock, Logger logger) {
        this.eventStore = eventStore;
        this.clock = clock != null ? clock : Clock.systemUTC();
        this.logger = logger != null ? logger : Logger.getLogger(TelemetryMetricsService.class.getName());
    }

    /**
     * Persists a Q1-Q3 lifecycle event in fail-open mode: write failures log a warning and never throw.
     */
    public boolean recordLifecycleEvent(TelemetryEvent event) {
        if (event == null || event.getEventType() == null) {
            logger.log(Level.WARNING, "Skipping non-lifecycle or null telemetry event");
            return false;
        }
        if (eventStore == null) {
            logger.log(Level.WARNING, "GQM lifecycle eventStore is not configured; skipping write for {0}",
                    event.getEventType());
            return false;
        }
        Instant timestamp = event.getRecordedAt() != null ? event.getRecordedAt() : clock.instant();
        try {
            eventStore.save(event, timestamp);
            return true;
        } catch (Exception ex) {
            logger.log(Level.WARNING,
                    "Non-fatal GQM telemetry write failure for " + event.getEventType() + ": " + ex.getMessage(),
                    ex);
            return false;
        }
    }

    /**
     * Executes a primary upload or record-edit operation and records GQM telemetry without letting
     * telemetry construction or storage failures affect the primary result.
     */
    public <T> T executeWithTelemetry(Supplier<T> primaryOperation, Function<T, TelemetryEvent> eventFactory) {
        Objects.requireNonNull(primaryOperation, "primaryOperation must not be null");
        T result = primaryOperation.get();
        if (eventFactory != null) {
            try {
                TelemetryEvent event = eventFactory.apply(result);
                recordLifecycleEvent(event);
            } catch (Exception ex) {
                logger.log(Level.WARNING,
                        "Non-fatal GQM telemetry capture failure: " + ex.getMessage(),
                        ex);
            }
        }
        return result;
    }

    public TelemetrySummary calculateSummary(List<TelemetryEvent> events) {
        if (events == null || events.isEmpty()) {
            return new TelemetrySummary(0.0, 0.0, 0.0, 0.0, 0);
        }

        long total = events.size();
        long successful = 0;
        long zeroResults = 0;
        List<Long> latencies = new ArrayList<>();

        for (TelemetryEvent event : events) {
            if (event.isSuccess()) {
                successful++;
            }
            if (event.getResultCount() == 0) {
                zeroResults++;
            }
            latencies.add(event.getLatencyMs());
        }

        Collections.sort(latencies);

        double successRatio = (double) successful / total;
        double zeroResultRate = (double) zeroResults / total;
        double medianLatency = calculatePercentile(latencies, 50.0);
        double p95Latency = calculatePercentile(latencies, 95.0);

        return new TelemetrySummary(successRatio, zeroResultRate, medianLatency, p95Latency, total);
    }

    public Map<String, Object> formatGqmKpiResponse(TelemetrySummary summary) {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("status", "UP");

        Map<String, Object> kpi = new LinkedHashMap<>();
        kpi.put("total_queries", summary.getTotalQueries());
        kpi.put("success_ratio", summary.getSuccessRatio());
        kpi.put("zero_result_rate", summary.getZeroResultRate());
        kpi.put("median_latency_ms", summary.getMedianLatencyMs());
        kpi.put("p95_latency_ms", summary.getP95LatencyMs());

        response.put("kpi", kpi);
        return response;
    }

    private double calculatePercentile(List<Long> sortedValues, double percentile) {
        if (sortedValues.isEmpty()) {
            return 0.0;
        }
        if (sortedValues.size() == 1) {
            return sortedValues.get(0);
        }
        if (percentile <= 0.0) {
            return sortedValues.get(0);
        }
        if (percentile >= 100.0) {
            return sortedValues.get(sortedValues.size() - 1);
        }

        int rank = (int) Math.ceil((percentile / 100.0) * sortedValues.size()) - 1;
        rank = Math.max(0, Math.min(rank, sortedValues.size() - 1));
        return sortedValues.get(rank);
    }
}
