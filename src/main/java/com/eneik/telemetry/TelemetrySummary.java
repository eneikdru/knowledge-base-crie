package com.eneik.telemetry;

public class TelemetrySummary {
    private final double successRatio;
    private final double zeroResultRate;
    private final double medianLatencyMs;
    private final double p95LatencyMs;
    private final long totalQueries;

    public TelemetrySummary(double successRatio, double zeroResultRate, double medianLatencyMs, double p95LatencyMs, long totalQueries) {
        this.successRatio = successRatio;
        this.zeroResultRate = zeroResultRate;
        this.medianLatencyMs = medianLatencyMs;
        this.p95LatencyMs = p95LatencyMs;
        this.totalQueries = totalQueries;
    }

    public double getSuccessRatio() {
        return successRatio;
    }

    public double getZeroResultRate() {
        return zeroResultRate;
    }

    public double getMedianLatencyMs() {
        return medianLatencyMs;
    }

    public double getP95LatencyMs() {
        return p95LatencyMs;
    }

    public long getTotalQueries() {
        return totalQueries;
    }
}
