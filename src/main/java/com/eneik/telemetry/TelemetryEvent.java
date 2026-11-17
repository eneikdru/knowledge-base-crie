package com.eneik.telemetry;

public class TelemetryEvent {
    private final long latencyMs;
    private final boolean success;
    private final int resultCount;

    public TelemetryEvent(long latencyMs, boolean success, int resultCount) {
        this.latencyMs = latencyMs;
        this.success = success;
        this.resultCount = resultCount;
    }

    public long getLatencyMs() {
        return latencyMs;
    }

    public boolean isSuccess() {
        return success;
    }

    public int getResultCount() {
        return resultCount;
    }
}
