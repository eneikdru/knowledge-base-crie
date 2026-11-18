package com.eneik.crie.services;

import org.springframework.stereotype.Service;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

@Service
public class InternalService {

    private final Map<String, List<Map<String, String>>> sessionStore = new ConcurrentHashMap<>();
    private static final String INSTITUTIONAL_BRAND = "CRIE Institutional AI Assistant";

    public String getBrandName() {
        return INSTITUTIONAL_BRAND;
    }

    public int getIndexedDocumentCount(int actualCount) {
        return Math.max(actualCount, 0);
    }

    public void saveSessionMessages(String sessionId, List<Map<String, String>> messages) {
        if (sessionId != null && messages != null) {
            sessionStore.put(sessionId, Collections.unmodifiableList(messages));
        }
    }

    public List<Map<String, String>> getSessionMessages(String sessionId) {
        if (sessionId == null) {
            return Collections.emptyList();
        }
        return sessionStore.getOrDefault(sessionId, Collections.emptyList());
    }

    public byte[] generateDocx(Map<String, Object> parameters) {
        String content = "DOCX Document generated for: " + parameters.toString();
        return content.getBytes(StandardCharsets.UTF_8);
    }

    public byte[] generateXlsx(Map<String, Object> parameters) {
        String content = "XLSX Spreadsheet generated for: " + parameters.toString();
        return content.getBytes(StandardCharsets.UTF_8);
    }

    public byte[] generatePdf(Map<String, Object> parameters) {
        String content = "%PDF-1.4\n" + parameters.toString();
        return content.getBytes(StandardCharsets.UTF_8);
    }

    public byte[] generateTargetedBundle(Map<String, Object> filterParams, List<String> matchingDocNames) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(baos)) {
            for (String docName : matchingDocNames) {
                ZipEntry entry = new ZipEntry(docName);
                zos.putNextEntry(entry);
                String payload = "Document content for " + docName + " filtered by " + filterParams.toString();
                zos.write(payload.getBytes(StandardCharsets.UTF_8));
                zos.closeEntry();
            }
        }
        return baos.toByteArray();
    }
}
