package com.eneik.telemetry;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class TelemetryMetricsServiceTest {

    @Test
    @DisplayName("Calculates zero-result rates and median query times from simulated search query sequences")
    public void testCalculateAggregations() {
        List<TelemetryEvent> events = Arrays.asList(
                new TelemetryEvent(100, true, 5),   // success, 5 results
                new TelemetryEvent(200, true, 0),   // success, 0 results (zero-result)
                new TelemetryEvent(300, false, 0),  // failure
                new TelemetryEvent(400, true, 12),  // success, 12 results
                new TelemetryEvent(500, true, 0)    // success, 0 results (zero-result)
        );

        TelemetryMetricsService service = new TelemetryMetricsService();
        TelemetrySummary summary = service.calculateSummary(events);

        // Total queries: 5
        // Successful queries: 4 -> success ratio = 4/5 = 0.8
        assertEquals(0.8, summary.getSuccessRatio(), 0.001);

        // Zero-result queries among successful: 2 out of 4 (or 2 out of 5 total queries depending on definition; here 2/5 = 0.4)
        assertEquals(0.4, summary.getZeroResultRate(), 0.001);

        // Latencies sorted: 100, 200, 300, 400, 500 -> median is 300
        assertEquals(300.0, summary.getMedianLatencyMs(), 0.001);

        // p95 latency: with 5 items, index = ceil(0.95 * 5) - 1 = 4 -> 500
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
}
