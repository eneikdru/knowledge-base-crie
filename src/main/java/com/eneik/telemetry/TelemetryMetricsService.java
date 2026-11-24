package com.eneik.telemetry;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class TelemetryMetricsService {

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
