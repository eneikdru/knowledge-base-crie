package com.eneik.telemetry.services;

import java.util.Collections;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Internal service for telemetry aggregation and normative routing coordination.
 */
public class InternalService {

    private final Map<String, Object> serviceMetadata = new ConcurrentHashMap<>();

    public InternalService() {
        serviceMetadata.put("status", "ACTIVE");
        serviceMetadata.put("service", "crie-normative-assistant");
        serviceMetadata.put("version", "1.0.0");
    }

    public Map<String, Object> getServiceMetadata() {
        return Collections.unmodifiableMap(serviceMetadata);
    }

    public boolean isHealthy() {
        return "ACTIVE".equals(serviceMetadata.get("status"));
    }
}
