package com.eneik.telemetry;

public class TelemetryEvent {
    private final long latencyMs;
    private final boolean success;
    private final int resultCount;
    private final boolean contingentQuery;
    private final boolean dbGrounded;
    private final int pdfDeduplicationCount;
    private final double slot11DbLookupMs;

    public TelemetryEvent(long latencyMs, boolean success, int resultCount) {
        this(latencyMs, success, resultCount, false, false, 0, 0.0);
    }

    public TelemetryEvent(
            long latencyMs,
            boolean success,
            int resultCount,
            boolean contingentQuery,
            boolean dbGrounded,
            int pdfDeduplicationCount,
            double slot11DbLookupMs) {
        if (pdfDeduplicationCount < 0) {
            throw new IllegalArgumentException("pdfDeduplicationCount must be non-negative");
        }
        if (!Double.isFinite(slot11DbLookupMs) || slot11DbLookupMs < 0.0) {
            throw new IllegalArgumentException("slot11DbLookupMs must be finite and non-negative");
        }
        this.latencyMs = latencyMs;
        this.success = success;
        this.resultCount = resultCount;
        this.contingentQuery = contingentQuery;
        this.dbGrounded = dbGrounded;
        this.pdfDeduplicationCount = pdfDeduplicationCount;
        this.slot11DbLookupMs = slot11DbLookupMs;
    }

    public static TelemetryEvent forContingentQuery(boolean dbGrounded, double slot11DbLookupMs) {
        return new TelemetryEvent(Math.round(slot11DbLookupMs), dbGrounded, dbGrounded ? 1 : 0, true, dbGrounded, 0, slot11DbLookupMs);
    }

    public static TelemetryEvent forPdfIngestion(int pdfDeduplicationCount) {
        return new TelemetryEvent(0L, true, 0, false, false, pdfDeduplicationCount, 0.0);
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

    public boolean isContingentQuery() {
        return contingentQuery;
    }

    public boolean isDbGrounded() {
        return dbGrounded;
    }

    public int getPdfDeduplicationCount() {
        return pdfDeduplicationCount;
    }

    public double getSlot11DbLookupMs() {
        return slot11DbLookupMs;
    }
}
