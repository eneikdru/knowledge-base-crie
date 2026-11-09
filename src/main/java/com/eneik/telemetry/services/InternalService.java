package com.eneik.telemetry.services;

import java.time.Instant;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.logging.Logger;

/**
 * InternalService provides operational health, request tracking,
 * and internal metrics aggregation for API services, including
 * the /api/chat normative assistant endpoint and document sanitization/download telemetry.
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

    private final AtomicLong totalNormativeSearches = new AtomicLong(0);
    private final AtomicLong totalDownloadsServed = new AtomicLong(0);
    private final AtomicLong totalSanitizedDocuments = new AtomicLong(0);

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

    /**
     * Records a normative search query execution for /api/search or /api/v1/normative/search.
     *
     * @param query       search query string
     * @param resultCount number of matching documents returned
     * @param success     whether the search completed successfully
     */
    public void recordNormativeSearch(String query, int resultCount, boolean success) {
        if (query == null || query.trim().isEmpty()) {
            recordCall("/api/v1/normative/search", false);
            throw new IllegalArgumentException("Search query cannot be empty");
        }
        recordCall("/api/v1/normative/search", success);
        totalNormativeSearches.incrementAndGet();
    }

    /**
     * Records a document download execution for /api/v1/normative/download/{id}.
     *
     * @param documentId the identifier of the requested normative document
     * @param format     document binary format (DOCX, PDF)
     * @param success    whether streaming succeeded
     */
    public void recordDocumentDownload(String documentId, String format, boolean success) {
        if (documentId == null || documentId.trim().isEmpty()) {
            recordCall("/api/v1/normative/download", false);
            throw new IllegalArgumentException("Document ID cannot be null or empty");
        }
        recordCall("/api/v1/normative/download/" + documentId.trim(), success);
        if (success) {
            totalDownloadsServed.incrementAndGet();
        }
    }

    /**
     * Sanitizes raw document metadata payloads by stripping relative/technical filesystem paths
     * and exposing clean human-readable titles, annotations, and download endpoints.
     *
     * @param rawPayload raw key-value document attributes from index storage
     * @return sanitized document payload safe for public API responses
     */
    public Map<String, Object> sanitizeDocumentPayload(Map<String, Object> rawPayload) {
        if (rawPayload == null) {
            return Collections.emptyMap();
        }
        Map<String, Object> sanitized = new HashMap<>(rawPayload);
        sanitized.remove("path");
        sanitized.remove("file_path");
        sanitized.remove("filePath");
        sanitized.remove("relative_path");
        sanitized.remove("relativePath");
        sanitized.remove("technical_path");
        sanitized.remove("filesystem_path");

        Object docId = rawPayload.getOrDefault("id", rawPayload.get("document_id"));
        if (docId != null) {
            String idStr = String.valueOf(docId);
            sanitized.put("id", idStr);
            sanitized.put("download_url", "/api/v1/normative/download/" + idStr);
        }

        if (!sanitized.containsKey("title") && rawPayload.containsKey("name")) {
            sanitized.put("title", rawPayload.get("name"));
        }
        if (!sanitized.containsKey("annotation") && rawPayload.containsKey("description")) {
            sanitized.put("annotation", rawPayload.get("description"));
        }

        totalSanitizedDocuments.incrementAndGet();
        return Collections.unmodifiableMap(sanitized);
    }

    /**
     * Generates streaming HTTP response headers for authentic document downloads,
     * ensuring Content-Disposition attachment headers prevent path leakage.
     *
     * @param documentId document ID
     * @param filename   clean attachment filename
     * @param format     document format (pdf, docx)
     * @return map of standard HTTP headers
     */
    public static Map<String, String> buildDownloadHeaders(String documentId, String filename, String format) {
        Map<String, String> headers = new HashMap<>();
        String cleanName = (filename != null && !filename.trim().isEmpty())
                ? filename.replaceAll("[^a-zA-Z0-9._-]", "_")
                : "normative_document_" + Objects.toString(documentId, "file");

        String extension = (format != null && format.equalsIgnoreCase("pdf")) ? ".pdf" : ".docx";
        if (!cleanName.toLowerCase().endsWith(extension)) {
            cleanName += extension;
        }

        headers.put("Content-Disposition", "attachment; filename=\"" + cleanName + "\"");
        if (".pdf".equals(extension)) {
            headers.put("Content-Type", "application/pdf");
        } else {
            headers.put("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
        }
        headers.put("X-Content-Type-Options", "nosniff");
        return Collections.unmodifiableMap(headers);
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

    public long getTotalNormativeSearches() {
        return totalNormativeSearches.get();
    }

    public long getTotalDownloadsServed() {
        return totalDownloadsServed.get();
    }

    public long getTotalSanitizedDocuments() {
        return totalSanitizedDocuments.get();
    }

    public boolean isHealthy() {
        return true;
    }

    public Instant getStartTime() {
        return startTime;
    }
}
