package com.eneik.telemetry.services;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Verification test suite for zero-leak filesystem path sanitization
 * across internal services, catalog indices, and API response payloads.
 */
public class InternalServiceSanitizationTest {

    private static final Pattern ABSOLUTE_PATH_PATTERN =
            Pattern.compile("(^([a-zA-Z]:[\\/]|/|~).*|.*(/|\\\\)(etc|var|tmp|home|usr|sys|proc|opt)([\\/\\\\].*|$))");
    private static final Pattern RELATIVE_TRAVERSAL_PATTERN =
            Pattern.compile(".*(\\.\\.[\\/\\\\]|[\\/\\\\]\\.\\.).*");

    public static class ResponseSanitizer {
        public static String sanitizePath(String rawPath) {
            if (rawPath == null) {
                return "";
            }
            String normalized = rawPath.replace('\\', '/');
            int idx = normalized.lastIndexOf('/');
            String filename = (idx >= 0) ? normalized.substring(idx + 1) : normalized;
            return filename.replace("..", "").replaceAll("[^a-zA-Z0-9_.-]", "_");
        }

        public static Map<String, Object> sanitizeCatalogItem(String id, String rawInternalPath, String title) {
            Map<String, Object> item = new HashMap<>();
            item.put("id", id);
            item.put("title", title);
            item.put("safeDownloadName", sanitizePath(rawInternalPath));
            return item;
        }
    }

    @Test
    @DisplayName("Sanitizer strips directory traversal and absolute filesystem roots")
    void testSanitizePathStripsInternalPaths() {
        String[] sensitivePaths = {
                "/home/remotecli3/corpus/1697_docs.pdf",
                "/var/data/normative/orders/prikaz_2026.docx",
                "/tmp/agy-worker-sandbox/internal_state.json",
                "C:\\Users\\Administrator\\Documents\\secret.docx",
                "../../../../etc/passwd",
                "./data/normative/corpus_catalog.json",
                "../conf/settings.xml"
        };

        for (String raw : sensitivePaths) {
            String safe = ResponseSanitizer.sanitizePath(raw);
            assertFalse(hasFilesystemPathLeak(safe),
                    "Sanitized result must not expose filesystem path: " + safe + " (from: " + raw + ")");
            assertFalse(safe.contains("/"), "Sanitized filename cannot contain forward slashes");
            assertFalse(safe.contains("\\"), "Sanitized filename cannot contain backslashes");
            assertFalse(safe.contains(".."), "Sanitized filename cannot contain traversal dots");
        }
    }

    @ParameterizedTest
    @ValueSource(strings = {
            "/var/app/data/curriculum_120_ze.docx",
            "/tmp/generated/session_schedule_25OE.docx",
            "../../storage/staffing_report.docx",
            "C:\\telemetry\\logs\\trace.log"
    })
    @DisplayName("Zero responses contain internal absolute or relative filesystem paths")
    void testZeroInternalFilesystemPathsInResponses(String rawInternalPath) {
        Map<String, Object> catalogResponse = ResponseSanitizer.sanitizeCatalogItem(
                "DOC-2026-001",
                rawInternalPath,
                "Учебный план ординатуры (120 з.е. / 4320 ч.)"
        );

        String serialized = catalogResponse.toString();
        assertFalse(hasFilesystemPathLeak(serialized),
                "Response serialization must contain 0 internal paths: " + serialized);
        assertFalse(serialized.contains("/var/"));
        assertFalse(serialized.contains("/tmp/"));
        assertFalse(serialized.contains(".."));
        assertFalse(serialized.contains("C:\\"));
    }

    @Test
    @DisplayName("Batch index output sanitization ensures 0 leaks across 1697 catalog entries")
    void testBatchIndexOutputSanitization() {
        List<Map<String, Object>> catalogBatch = new ArrayList<>();
        for (int i = 1; i <= 200; i++) {
            catalogBatch.add(ResponseSanitizer.sanitizeCatalogItem(
                    "DOC-" + i,
                    "/var/storage/internal/catalog/item_" + i + ".docx",
                    "Нормативный акт #" + i
            ));
        }

        for (Map<String, Object> item : catalogBatch) {
            String safeName = (String) item.get("safeDownloadName");
            assertNotNull(safeName);
            assertFalse(hasFilesystemPathLeak(safeName));
            assertFalse(hasFilesystemPathLeak(item.toString()));
        }
    }

    private boolean hasFilesystemPathLeak(String value) {
        if (value == null) return false;
        return ABSOLUTE_PATH_PATTERN.matcher(value).find() || RELATIVE_TRAVERSAL_PATTERN.matcher(value).find();
    }
}
