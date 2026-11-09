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
 * and internal metrics aggregation for API services.
 */
public class InternalService {

    private static final Logger LOGGER = Logger.getLogger(InternalService.class.getName());

    private final AtomicLong totalRequests = new AtomicLong(0);
    private final AtomicLong successfulRequests = new AtomicLong(0);
    private final AtomicLong failedRequests = new AtomicLong(0);
    private final Map<String, AtomicLong> endpointHits = new ConcurrentHashMap<>();
    private final Instant startTime = Instant.now();

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

    public boolean isHealthy() {
        return true;
    }

    public Instant getStartTime() {
        return startTime;
    }
}
