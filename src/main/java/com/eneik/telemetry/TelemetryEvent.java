package com.eneik.telemetry;

import java.time.Instant;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

/**
 * Telemetry event representing either legacy search metrics or GQM Q1-Q3 document-lifecycle events.
 */
public class TelemetryEvent {

    /**
     * GQM lifecycle event categories mapped strictly to Questions Q1-Q3.
     */
    public enum LifecycleEventType {
        UPLOAD_DEDUPLICATION("Q1"),
        REGISTRY_CORRECTION("Q2"),
        UPLOAD_HELP_CHAT("Q3");

        private final String questionId;

        LifecycleEventType(String questionId) {
            this.questionId = questionId;
        }

        public String getQuestionId() {
            return questionId;
        }
    }

    public static final Set<String> ALLOWED_REGISTRY_TABLES = Collections.unmodifiableSet(
            new HashSet<>(Arrays.asList("enrolled_trainees", "pps_staff", "rup_curricula")));

    private final long latencyMs;
    private final boolean success;
    private final int resultCount;
    private final LifecycleEventType eventType;
    private final Instant recordedAt;
    private final Boolean deduplicated;
    private final String targetTable;
    private final Integer lifecycleResultCount;

    public TelemetryEvent(long latencyMs, boolean success, int resultCount) {
        this.latencyMs = latencyMs;
        this.success = success;
        this.resultCount = resultCount;
        this.eventType = null;
        this.recordedAt = null;
        this.deduplicated = null;
        this.targetTable = null;
        this.lifecycleResultCount = null;
    }

    private TelemetryEvent(
            LifecycleEventType eventType,
            Instant recordedAt,
            boolean success,
            Boolean deduplicated,
            String targetTable,
            Integer lifecycleResultCount,
            long latencyMs) {
        if (latencyMs < 0) {
            throw new IllegalArgumentException("latencyMs must be non-negative");
        }
        this.eventType = Objects.requireNonNull(eventType, "eventType must not be null");
        this.recordedAt = recordedAt;
        this.success = success;
        this.deduplicated = deduplicated;
        this.targetTable = targetTable;
        this.lifecycleResultCount = lifecycleResultCount;
        this.resultCount = lifecycleResultCount != null ? lifecycleResultCount : 0;
        this.latencyMs = latencyMs;
    }

    /**
     * Creates a Q1 upload deduplication event containing only Q1-required fields.
     */
    public static TelemetryEvent uploadDeduplication(
            boolean deduplicated, boolean success, long latencyMs, Instant recordedAt) {
        return new TelemetryEvent(
                LifecycleEventType.UPLOAD_DEDUPLICATION,
                recordedAt,
                success,
                deduplicated,
                null,
                null,
                latencyMs);
    }

    public static TelemetryEvent uploadDeduplication(boolean deduplicated, boolean success, long latencyMs) {
        return uploadDeduplication(deduplicated, success, latencyMs, null);
    }

    /**
     * Creates a Q2 registry correction event restricted to allowlisted registry tables.
     */
    public static TelemetryEvent registryCorrection(
            String targetTable, boolean success, long latencyMs, Instant recordedAt) {
        if (targetTable == null || !ALLOWED_REGISTRY_TABLES.contains(targetTable)) {
            throw new IllegalArgumentException("Unsupported registry targetTable: " + targetTable);
        }
        return new TelemetryEvent(
                LifecycleEventType.REGISTRY_CORRECTION,
                recordedAt,
                success,
                null,
                targetTable,
                null,
                latencyMs);
    }

    public static TelemetryEvent registryCorrection(String targetTable, boolean success, long latencyMs) {
        return registryCorrection(targetTable, success, latencyMs, null);
    }

    /**
     * Creates a Q3 upload-help chat event containing only Q3-required fields.
     */
    public static TelemetryEvent uploadHelpChat(
            int resultCount, boolean success, long latencyMs, Instant recordedAt) {
        if (resultCount < 0) {
            throw new IllegalArgumentException("resultCount must be non-negative");
        }
        return new TelemetryEvent(
                LifecycleEventType.UPLOAD_HELP_CHAT,
                recordedAt,
                success,
                null,
                null,
                resultCount,
                latencyMs);
    }

    public static TelemetryEvent uploadHelpChat(int resultCount, boolean success, long latencyMs) {
        return uploadHelpChat(resultCount, success, latencyMs, null);
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

    public LifecycleEventType getEventType() {
        return eventType;
    }

    public String getQuestionId() {
        return eventType != null ? eventType.getQuestionId() : null;
    }

    public Instant getRecordedAt() {
        return recordedAt;
    }

    public Boolean getDeduplicated() {
        return deduplicated;
    }

    public String getTargetTable() {
        return targetTable;
    }

    public Integer getLifecycleResultCount() {
        return lifecycleResultCount;
    }
}
