package com.eneik.telemetry;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Proxy;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class TelemetryMetricsServiceTest {

    private static final Instant FIXED_INSTANT = Instant.parse("2026-11-24T12:00:00Z");
    private static final Clock FIXED_CLOCK = Clock.fixed(FIXED_INSTANT, ZoneOffset.UTC);

    @Test
    @DisplayName("Calculates zero-result rates and median query times from simulated search query sequences")
    public void testCalculateAggregations() {
        List<TelemetryEvent> events = Arrays.asList(
                new TelemetryEvent(100, true, 5),
                new TelemetryEvent(200, true, 0),
                new TelemetryEvent(300, false, 0),
                new TelemetryEvent(400, true, 12),
                new TelemetryEvent(500, true, 0)
        );

        TelemetryMetricsService service = new TelemetryMetricsService();
        TelemetrySummary summary = service.calculateSummary(events);

        assertEquals(0.8, summary.getSuccessRatio(), 0.001);
        assertEquals(0.4, summary.getZeroResultRate(), 0.001);
        assertEquals(300.0, summary.getMedianLatencyMs(), 0.001);
        assertEquals(500.0, summary.getP95LatencyMs(), 0.001);
    }

    @Test
    @DisplayName("Empty event stream returns safe zero/default telemetry metrics")
    public void testEmptyEventsSummary() {
        TelemetryMetricsService service = new TelemetryMetricsService();
        TelemetrySummary summary = service.calculateSummary(Collections.emptyList());

        assertEquals(0.0, summary.getSuccessRatio(), 0.001);
        assertEquals(0.0, summary.getZeroResultRate(), 0.001);
        assertEquals(0.0, summary.getMedianLatencyMs(), 0.001);
        assertEquals(0.0, summary.getP95LatencyMs(), 0.001);
    }

    @Test
    @DisplayName("Status endpoint renders valid GQM KPI JSON summary")
    public void testGqmStatusEndpointSummary() {
        TelemetryMetricsService service = new TelemetryMetricsService();
        List<TelemetryEvent> events = Arrays.asList(
                new TelemetryEvent(150, true, 3),
                new TelemetryEvent(250, true, 1)
        );
        TelemetrySummary summary = service.calculateSummary(events);
        Map<String, Object> kpiSummary = service.formatGqmKpiResponse(summary);

        assertNotNull(kpiSummary);
        assertTrue(kpiSummary.containsKey("status"));
        assertEquals("UP", kpiSummary.get("status"));
        assertTrue(kpiSummary.containsKey("kpi"));

        @SuppressWarnings("unchecked")
        Map<String, Object> kpiDetails = (Map<String, Object>) kpiSummary.get("kpi");
        assertEquals(1.0, ((Number) kpiDetails.get("success_ratio")).doubleValue(), 0.001);
        assertEquals(0.0, ((Number) kpiDetails.get("zero_result_rate")).doubleValue(), 0.001);
        assertEquals(200.0, ((Number) kpiDetails.get("median_latency_ms")).doubleValue(), 0.001);
        assertEquals(250.0, ((Number) kpiDetails.get("p95_latency_ms")).doubleValue(), 0.001);
    }

    @Test
    @DisplayName("Records Q1-Q3 lifecycle events with strict minimal columns and deterministic timestamps")
    public void testRecordQ1ToQ3LifecycleEventsStrictFields() {
        List<String> executedSql = new ArrayList<>();
        List<Map<Integer, Object>> insertedRows = new ArrayList<>();

        TelemetryMetricsService.JdbcSqliteEventStore store = new TelemetryMetricsService.JdbcSqliteEventStore(
                () -> createRecordingConnection(executedSql, insertedRows));
        TelemetryMetricsService service = new TelemetryMetricsService(store, FIXED_CLOCK, createQuietLogger());

        assertTrue(service.recordLifecycleEvent(TelemetryEvent.uploadDeduplication(true, true, 18L)));
        assertTrue(service.recordLifecycleEvent(TelemetryEvent.registryCorrection("enrolled_trainees", true, 42L)));
        assertTrue(service.recordLifecycleEvent(TelemetryEvent.uploadHelpChat(3, true, 27L)));

        assertTrue(executedSql.contains(TelemetryMetricsService.GQM_EVENTS_TABLE_DDL));
        assertEquals(3, insertedRows.size());

        Map<Integer, Object> q1 = insertedRows.get(0);
        assertEquals("Q1", q1.get(1));
        assertEquals("UPLOAD_DEDUPLICATION", q1.get(2));
        assertEquals(FIXED_INSTANT.toString(), q1.get(3));
        assertEquals(1, q1.get(4));
        assertEquals(1, q1.get(5));
        assertNull(q1.get(6));
        assertNull(q1.get(7));
        assertEquals(18L, q1.get(8));

        Map<Integer, Object> q2 = insertedRows.get(1);
        assertEquals("Q2", q2.get(1));
        assertEquals("REGISTRY_CORRECTION", q2.get(2));
        assertEquals(FIXED_INSTANT.toString(), q2.get(3));
        assertEquals(1, q2.get(4));
        assertNull(q2.get(5));
        assertEquals("enrolled_trainees", q2.get(6));
        assertNull(q2.get(7));
        assertEquals(42L, q2.get(8));

        Map<Integer, Object> q3 = insertedRows.get(2);
        assertEquals("Q3", q3.get(1));
        assertEquals("UPLOAD_HELP_CHAT", q3.get(2));
        assertEquals(FIXED_INSTANT.toString(), q3.get(3));
        assertEquals(1, q3.get(4));
        assertNull(q3.get(5));
        assertNull(q3.get(6));
        assertEquals(3, q3.get(7));
        assertEquals(27L, q3.get(8));
    }

    @Test
    @DisplayName("Rejects unsupported registry table names outside structured DB targets")
    public void testRejectsUnsupportedRegistryTable() {
        assertThrows(IllegalArgumentException.class,
                () -> TelemetryEvent.registryCorrection("arbitrary_table", true, 10L));
    }

    @Test
    @DisplayName("Simulated telemetry write failure logs non-fatal warning while primary upload and edit succeed")
    public void testFailOpenOnSimulatedTelemetryWriteFailure() {
        List<LogRecord> warningLogs = new ArrayList<>();
        Logger logger = createCapturingLogger(warningLogs);

        TelemetryMetricsService.LifecycleEventStore failingStore = (event, recordedAt) -> {
            throw new SQLException("simulated disk I/O error");
        };
        TelemetryMetricsService service = new TelemetryMetricsService(failingStore, FIXED_CLOCK, logger);

        String uploadOutcome = service.executeWithTelemetry(
                () -> "upload-ok",
                outcome -> TelemetryEvent.uploadDeduplication(true, true, 12L));
        assertEquals("upload-ok", uploadOutcome);

        String editOutcome = service.executeWithTelemetry(
                () -> "edit-ok",
                outcome -> TelemetryEvent.registryCorrection("pps_staff", true, 25L));
        assertEquals("edit-ok", editOutcome);

        assertFalse(service.recordLifecycleEvent(TelemetryEvent.uploadHelpChat(2, true, 9L)));

        assertEquals(3, warningLogs.size());
        for (LogRecord record : warningLogs) {
            assertEquals(Level.WARNING, record.getLevel());
            assertTrue(record.getMessage().contains("Non-fatal GQM telemetry write failure"));
        }
    }

    private static Logger createQuietLogger() {
        Logger logger = Logger.getLogger("TelemetryMetricsServiceTest.quiet");
        logger.setUseParentHandlers(false);
        return logger;
    }

    private static Logger createCapturingLogger(List<LogRecord> records) {
        Logger logger = Logger.getLogger("TelemetryMetricsServiceTest.capturing." + System.nanoTime());
        logger.setUseParentHandlers(false);
        logger.setLevel(Level.ALL);
        logger.addHandler(new Handler() {
            @Override
            public void publish(LogRecord record) {
                records.add(record);
            }

            @Override
            public void flush() {
            }

            @Override
            public void close() {
            }
        });
        return logger;
    }

    private static Connection createRecordingConnection(
            List<String> executedSql, List<Map<Integer, Object>> insertedRows) {
        Statement stmtProxy = (Statement) Proxy.newProxyInstance(
                Statement.class.getClassLoader(),
                new Class<?>[]{Statement.class},
                (proxy, method, args) -> {
                    if ("execute".equals(method.getName()) && args != null && args.length == 1) {
                        executedSql.add((String) args[0]);
                        return Boolean.FALSE;
                    }
                    return null;
                });

        return (Connection) Proxy.newProxyInstance(
                Connection.class.getClassLoader(),
                new Class<?>[]{Connection.class},
                (proxy, method, args) -> {
                    String name = method.getName();
                    if ("createStatement".equals(name)) {
                        return stmtProxy;
                    }
                    if ("prepareStatement".equals(name) && args != null && args.length >= 1) {
                        executedSql.add((String) args[0]);
                        Map<Integer, Object> bound = new HashMap<>();
                        return Proxy.newProxyInstance(
                                PreparedStatement.class.getClassLoader(),
                                new Class<?>[]{PreparedStatement.class},
                                (psProxy, psMethod, psArgs) -> {
                                    String psName = psMethod.getName();
                                    if (("setString".equals(psName)
                                            || "setInt".equals(psName)
                                            || "setLong".equals(psName))
                                            && psArgs != null && psArgs.length == 2) {
                                        bound.put((Integer) psArgs[0], psArgs[1]);
                                        return null;
                                    }
                                    if ("setNull".equals(psName) && psArgs != null && psArgs.length >= 1) {
                                        bound.put((Integer) psArgs[0], null);
                                        return null;
                                    }
                                    if ("executeUpdate".equals(psName)) {
                                        insertedRows.add(new HashMap<>(bound));
                                        return 1;
                                    }
                                    return null;
                                });
                    }
                    return null;
                });
    }
}
