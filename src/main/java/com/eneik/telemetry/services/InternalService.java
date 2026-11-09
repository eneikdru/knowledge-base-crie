package com.eneik.telemetry.services;

import java.time.Instant;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.logging.Logger;

/**
 * InternalService provides operational health, request tracking,
 * and internal metrics aggregation for API services, including
 * the /api/chat normative assistant endpoint.
 */
public class InternalService {

    private static final Logger LOGGER = Logger.getLogger(InternalService.class.getName());

    private final AtomicLong totalRequests = new AtomicLong(0);
    private final AtomicLong successfulRequests = new AtomicLong(0);
    private final AtomicLong failedRequests = new AtomicLong(0);
    private final Map<String, AtomicLong> endpointHits = new ConcurrentHashMap<>();
    private final Instant startTime = Instant.now();

    private final AtomicLong totalChatQueries = new AtomicLong(0);
    private final AtomicLong totalCitationsServed = new AtomicLong(0);
    private final AtomicLong totalChatDurationMs = new AtomicLong(0);

    public InternalService() {
    }

    public void recordCall(String endpoint, boolean success) {
        if (endpoint == null || endpoint.trim().isEmpty()) {
            throw new IllegalArgumentException("Endpoint cannot be null or empty");
        }
        totalRequests.incrementAndGet();
        if (success) {
            successfulRequests.incrementAndGet();
        } else {
            failedRequests.incrementAndGet();
        }
        endpointHits.computeIfAbsent(endpoint, k -> new AtomicLong(0)).incrementAndGet();
        LOGGER.fine(() -> String.format("InternalService call recorded for %s (success=%s)", endpoint, success));
    }

    /**
     * Validates and records a chat query execution for the /api/chat endpoint.
     *
     * @param query       the incoming user question
     * @param durationMs  elapsed execution time in milliseconds
     * @param citations   number of grounded citation paths returned
     * @param success     whether the chat query succeeded
     */
    public void recordChatQuery(String query, long durationMs, int citations, boolean success) {
        if (query == null || query.trim().isEmpty()) {
            recordCall("/api/chat", false);
            throw new IllegalArgumentException("Текст запроса не может быть пустым или состоять только из пробелов");
        }
        recordCall("/api/chat", success);
        totalChatQueries.incrementAndGet();
        if (citations > 0) {
            totalCitationsServed.addAndGet(citations);
        }
        if (durationMs > 0) {
            totalChatDurationMs.addAndGet(durationMs);
        }
    }

    public long getTotalRequests() {
        return totalRequests.get();
    }

    public long getSuccessfulRequests() {
        return successfulRequests.get();
    }

    public long getFailedRequests() {
        return failedRequests.get();
    }

    public Map<String, Long> getEndpointHits() {
        Map<String, Long> snapshot = new HashMap<>();
        endpointHits.forEach((k, v) -> snapshot.put(k, v.get()));
        return Collections.unmodifiableMap(snapshot);
    }

    public long getTotalChatQueries() {
        return totalChatQueries.get();
    }

    public long getTotalCitationsServed() {
        return totalCitationsServed.get();
    }

    public double getAverageChatDurationMs() {
        long queries = totalChatQueries.get();
        return queries > 0 ? (double) totalChatDurationMs.get() / queries : 0.0;
    }

    public boolean isHealthy() {
        return true;
    }

    public Instant getStartTime() {
        return startTime;
    }
}
