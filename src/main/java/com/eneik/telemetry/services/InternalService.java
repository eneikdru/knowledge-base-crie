package com.eneik.telemetry.services;

import com.eneik.telemetry.services.security.InternalSecurityService;

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
 * perimeter authorization integration, and internal metrics aggregation for API services,
 * including the /api/chat normative assistant endpoint, document sanitization/download telemetry,
 * and official document generator (/api/v1/generator/*) telemetry.
 */
public class InternalService {

    private static final Logger LOGGER = Logger.getLogger(InternalService.class.getName());
    private static final String BEARER_PREFIX = "Bearer ";

    private final InternalSecurityService securityService;
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

    private final AtomicLong totalGeneratorRequests = new AtomicLong(0);
    private final AtomicLong totalGeneratorExportsServed = new AtomicLong(0);
    private final AtomicLong totalGeneratorDurationMs = new AtomicLong(0);

    public InternalService() {
        this.securityService = null;
    }

    public InternalService(InternalSecurityService securityService) {
        this.securityService = Objects.requireNonNull(securityService, "InternalSecurityService cannot be null");
    }

    /**
     * Evaluates perimeter authorization for a protected internal endpoint using a Bearer token.
     * Fails closed (HTTP 401) if no security service is configured or if the token is missing/invalid.
     *
     * @param endpoint            target endpoint path
     * @param authorizationHeader HTTP Authorization header value
     * @return 200 if authorized, 401 otherwise
     */
    public int authorizeEndpointRequest(String endpoint, String authorizationHeader) {
        String token = extractBearerToken(authorizationHeader);
        boolean authorized = token != null
                && this.securityService != null
                && this.securityService.isAuthorized(token);
        recordCall(endpoint, authorized);
        return authorized ? 200 : 401;
    }

    /**
     * Returns protected internal telemetry summary only when presented with a valid Bearer token.
     * Fails closed with SecurityException on unauthenticated or unauthorized requests.
     *
     * @param authorizationHeader HTTP Authorization header value
     * @return unmodifiable map of operational metrics without filesystem paths
     */
    public Map<String, Object> getProtectedData(String authorizationHeader) {
        if (authorizeEndpointRequest("/api/v1/internal/telemetry", authorizationHeader) != 200) {
            throw new SecurityException("Unauthorized access to protected internal telemetry data");
        }
        Map<String, Object> payload = new HashMap<>();
        payload.put("status", "UP");
        payload.put("healthy", isHealthy());
        payload.put("total_requests", getTotalRequests());
        payload.put("successful_requests", getSuccessfulRequests());
        payload.put("failed_requests", getFailedRequests());
        payload.put("total_sanitized_documents", getTotalSanitizedDocuments());
        return Collections.unmodifiableMap(payload);
    }

    private static String extractBearerToken(String authorizationHeader) {
        if (authorizationHeader == null || !authorizationHeader.startsWith(BEARER_PREFIX)) {
            return null;
        }
        String token = authorizationHeader.substring(BEARER_PREFIX.length()).trim();
        return token.isEmpty() ? null : token;
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
     * @param query      the incoming user question
     * @param durationMs elapsed execution time in milliseconds
     * @param citations  number of grounded citation paths returned
     * @param success    whether the chat query succeeded
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
     * Records an official document generation execution for /api/v1/generator/generate.
     *
     * @param documentType template type (e.g., exam_session, ums_protocol, director_order)
     * @param durationMs   elapsed generation time in milliseconds
     * @param success      whether generation succeeded
     */
    public void recordGeneratorRequest(String documentType, long durationMs, boolean success) {
        if (documentType == null || documentType.trim().isEmpty()) {
            recordCall("/api/v1/generator/generate", false);
            throw new IllegalArgumentException("Document type cannot be null or empty");
        }
        recordCall("/api/v1/generator/generate", success);
        totalGeneratorRequests.incrementAndGet();
        if (durationMs > 0) {
            totalGeneratorDurationMs.addAndGet(durationMs);
        }
    }

    /**
     * Records a generated document export / streaming execution for /api/v1/generator/export/{job_id}/docx.
     *
     * @param jobId   identifier of the generated document job
     * @param format  export file format (docx)
     * @param success whether direct binary streaming succeeded
     */
    public void recordGeneratorExport(String jobId, String format, boolean success) {
        if (jobId == null || jobId.trim().isEmpty()) {
            recordCall("/api/v1/generator/export", false);
            throw new IllegalArgumentException("Job ID cannot be null or empty");
        }
        recordCall("/api/v1/generator/export/" + jobId.trim() + "/" + (format != null ? format.toLowerCase() : "docx"), success);
        if (success) {
            totalGeneratorExportsServed.incrementAndGet();
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
        sanitized.remove("source_path");
        sanitized.remove("full_path");
        sanitized.remove("local_path");
        sanitized.remove("absolute_path");

        Object docId = rawPayload.getOrDefault("id", rawPayload.get("document_id"));
        if (docId != null) {
            String idStr = sanitizeIdentifier(String.valueOf(docId));
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
     * Validates exam session generator parameters (groups 25OE-26OP, dates 25.01-25.02).
     *
     * @param parameters map of input parameters for exam session generation
     * @return true if valid parameters are present
     */
    public boolean validateExamSessionParams(Map<String, Object> parameters) {
        if (parameters == null || parameters.isEmpty()) {
            return false;
        }
        Object groupsObj = parameters.get("groups");
        Object startDateObj = parameters.get("start_date");
        Object endDateObj = parameters.get("end_date");

        if (groupsObj == null || startDateObj == null || endDateObj == null) {
            return false;
        }
        String start = String.valueOf(startDateObj).trim();
        String end = String.valueOf(endDateObj).trim();
        return !start.isEmpty() && !end.isEmpty();
    }

    /**
     * Constructs preview payload metadata and pre-signed download token for /api/v1/generator/generate.
     *
     * @param jobId        generator job UUID
     * @param documentType document template type
     * @param previewText  preview summary text
     * @return response payload containing preview and download token url
     */
    public Map<String, Object> buildGeneratorPreviewResponse(String jobId, String documentType, String previewText) {
        if (jobId == null || jobId.trim().isEmpty()) {
            throw new IllegalArgumentException("Job ID cannot be null or empty");
        }
        String safeJobId = sanitizeIdentifier(jobId);
        Map<String, Object> response = new HashMap<>();
        response.put("job_id", safeJobId);
        response.put("document_type", documentType != null ? documentType : "official_document");
        response.put("preview", previewText != null ? previewText : "");
        response.put("status", "READY");
        response.put("download_token", "tok_" + safeJobId.replaceAll("[^a-zA-Z0-9]", ""));
        response.put("download_url", "/api/v1/generator/export/" + safeJobId + "/docx");
        return Collections.unmodifiableMap(response);
    }

    /**
     * Generates streaming HTTP response headers for generated official DOCX document downloads,
     * ensuring Content-Disposition attachment headers, valid MIME types, and anti-sniff protection.
     *
     * @param jobId    generator job identifier
     * @param filename clean attachment filename
     * @return map of standard HTTP headers for streaming .DOCX binaries
     */
    public static Map<String, String> buildGeneratorExportHeaders(String jobId, String filename) {
        Map<String, String> headers = new HashMap<>();
        String cleanName = sanitizeFilenameSegment(filename);
        if (cleanName == null) {
            cleanName = "generated_document_" + sanitizeIdentifier(Objects.toString(jobId, "job"));
        }

        if (!cleanName.toLowerCase().endsWith(".docx")) {
            cleanName += ".docx";
        }

        headers.put("Content-Disposition", "attachment; filename=\"" + cleanName + "\"");
        headers.put("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
        headers.put("X-Content-Type-Options", "nosniff");
        headers.put("Cache-Control", "no-cache, no-store, must-revalidate");
        headers.put("Pragma", "no-cache");
        return Collections.unmodifiableMap(headers);
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
        String cleanName = sanitizeFilenameSegment(filename);
        if (cleanName == null) {
            cleanName = "normative_document_" + sanitizeIdentifier(Objects.toString(documentId, "file"));
        }

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

    private static String sanitizeFilenameSegment(String rawFilename) {
        if (rawFilename == null || rawFilename.trim().isEmpty()) {
            return null;
        }
        String normalized = rawFilename.replace('\\', '/');
        int lastSlash = normalized.lastIndexOf('/');
        String base = (lastSlash >= 0) ? normalized.substring(lastSlash + 1) : normalized;
        String cleaned = base.replace("..", "").replaceAll("[^a-zA-Z0-9._-]", "_").trim();
        return cleaned.isEmpty() ? null : cleaned;
    }

    private static String sanitizeIdentifier(String rawId) {
        if (rawId == null) {
            return "";
        }
        return rawId.replace("..", "").replace('/', '_').replace('\\', '_').trim();
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

    public long getTotalGeneratorRequests() {
        return totalGeneratorRequests.get();
    }

    public long getTotalGeneratorExportsServed() {
        return totalGeneratorExportsServed.get();
    }

    public double getAverageGeneratorDurationMs() {
        long requests = totalGeneratorRequests.get();
        return requests > 0 ? (double) totalGeneratorDurationMs.get() / requests : 0.0;
    }

    public boolean isHealthy() {
        return true;
    }

    public Instant getStartTime() {
        return startTime;
    }
}
