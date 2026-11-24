package com.eneik.telemetry;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class TelemetryMetricsService {

    public static final Set<String> CONTINGENT_GQM_METRIC_KEYS = Collections.unmodifiableSet(
            new LinkedHashSet<>(Arrays.asList(
                    "contingent_db_grounded_query_rate",
                    "pdf_deduplication_count",
                    "slot11_db_lookup_ms")));

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

    public Map<String, Object> calculateContingentGqmMetrics(List<TelemetryEvent> events) {
        long contingentCount = 0;
        long groundedCount = 0;
        int pdfDeduplicationCount = 0;
        double totalSlot11LookupMs = 0.0;

        if (events != null) {
            for (TelemetryEvent event : events) {
                if (event == null) {
                    continue;
                }
                pdfDeduplicationCount += event.getPdfDeduplicationCount();
                if (event.isContingentQuery()) {
                    contingentCount++;
                    if (event.isDbGrounded()) {
                        groundedCount++;
                    }
                    totalSlot11LookupMs += event.getSlot11DbLookupMs();
                }
            }
        }

        double groundedRate = contingentCount > 0 ? (double) groundedCount / contingentCount : 0.0;
        double avgSlot11LookupMs = contingentCount > 0 ? totalSlot11LookupMs / contingentCount : 0.0;

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("contingent_db_grounded_query_rate", groundedRate);
        metrics.put("pdf_deduplication_count", pdfDeduplicationCount);
        metrics.put("slot11_db_lookup_ms", avgSlot11LookupMs);
        return metrics;
    }

    public Map<String, Object> formatContingentGqmPayload(List<TelemetryEvent> events) {
        Map<String, Object> gqm = new LinkedHashMap<>();
        gqm.put("goal", "Ensure contingent registry queries are reliably grounded in persistent DB records with deduplicated PDF ingestion and fast slot [11] lookup");

        List<Map<String, String>> questions = new ArrayList<>();
        questions.add(buildGqmQuestion("Q1", "What proportion of contingent queries are grounded in persistent admission_records?", "contingent_db_grounded_query_rate"));
        questions.add(buildGqmQuestion("Q2", "How many duplicate PDF files were deduplicated during ingestion?", "pdf_deduplication_count"));
        questions.add(buildGqmQuestion("Q3", "What is the slot [11] persistent DB lookup latency in milliseconds?", "slot11_db_lookup_ms"));

        gqm.put("questions", questions);
        gqm.put("metrics", calculateContingentGqmMetrics(events));
        return gqm;
    }

    private Map<String, String> buildGqmQuestion(String id, String question, String metric) {
        Map<String, String> entry = new LinkedHashMap<>();
        entry.put("id", id);
        entry.put("question", question);
        entry.put("metric", metric);
        return entry;
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
