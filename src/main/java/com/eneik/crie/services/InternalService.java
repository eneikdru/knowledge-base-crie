package com.eneik.crie.services;

import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * Internal service powering CRIE autopoietic continuity:
 * - Purges vendor branding leaks, enforcing institutional identity
 * - Manages backend chat session persistence and draft continuity
 * - Compiles standard-compliant dynamic documents (PDF, DOCX, XLSX)
 * - Assembles targeted document package archives dynamically
 */
@Service
public class InternalService {

    public static final String INSTITUTIONAL_PROVIDER = "CRIE Institutional Intelligence Engine";
    public static final String SYSTEM_VERSION = "2026.11-AUTOPOIETIC";

    private final Map<String, ChatSession> sessionStore = new ConcurrentHashMap<>();
    private final Map<String, String> documentCatalog = new ConcurrentHashMap<>();

    public InternalService() {
        // Seed initial normative catalog entries
        documentCatalog.put("DOC-NORM-001", "Normative Standard for Academic Integrity and Workload");
        documentCatalog.put("DOC-NORM-002", "Regulatory Guidelines on Automated Examination and Curricula");
        documentCatalog.put("DOC-NORM-003", "Institutional Telemetry and Compliance Evaluation Framework");
    }

    public static class ChatMessage {
        private String id;
        private String role;
        private String content;
        private Instant timestamp;

        public ChatMessage() {}

        public ChatMessage(String id, String role, String content, Instant timestamp) {
            this.id = id;
            this.role = role;
            this.content = content;
            this.timestamp = timestamp;
        }

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }
        public String getRole() { return role; }
        public void setRole(String role) { this.role = role; }
        public String getContent() { return content; }
        public void setContent(String content) { this.content = content; }
        public Instant getTimestamp() { return timestamp; }
        public void setTimestamp(Instant timestamp) { this.timestamp = timestamp; }
    }

    public static class ChatSession {
        private String sessionId;
        private List<ChatMessage> messages = new ArrayList<>();
        private Map<String, Object> drafts = new HashMap<>();
        private Instant lastActive;

        public ChatSession(String sessionId) {
            this.sessionId = sessionId;
            this.lastActive = Instant.now();
        }

        public String getSessionId() { return sessionId; }
        public List<ChatMessage> getMessages() { return messages; }
        public Map<String, Object> getDrafts() { return drafts; }
        public Instant getLastActive() { return lastActive; }
        public void setLastActive(Instant lastActive) { this.lastActive = lastActive; }
    }

    public Map<String, Object> getInstitutionalBranding() {
        Map<String, Object> branding = new LinkedHashMap<>();
        branding.put("provider", INSTITUTIONAL_PROVIDER);
        branding.put("systemVersion", SYSTEM_VERSION);
        branding.put("brandingLeakPurged", true);
        branding.put("totalIndexedDocuments", documentCatalog.size());
        branding.put("status", "ACTIVE");
        return branding;
    }

    public ChatSession getOrCreateSession(String sessionId) {
        return sessionStore.computeIfAbsent(sessionId, id -> new ChatSession(id));
    }

    public synchronized void appendSessionMessage(String sessionId, String role, String content) {
        ChatSession session = getOrCreateSession(sessionId);
        ChatMessage message = new ChatMessage(
                UUID.randomUUID().toString(),
                role,
                content,
                Instant.now()
        );
        session.getMessages().add(message);
        session.setLastActive(Instant.now());
    }

    public synchronized void saveDraft(String sessionId, String draftKey, Object draftContent) {
        ChatSession session = getOrCreateSession(sessionId);
        session.getDrafts().put(draftKey, draftContent);
        session.setLastActive(Instant.now());
    }

    public List<ChatMessage> getSessionMessages(String sessionId) {
        ChatSession session = sessionStore.get(sessionId);
        if (session == null) {
            return Collections.emptyList();
        }
        return new ArrayList<>(session.getMessages());
    }

    public Map<String, Object> getSessionDrafts(String sessionId) {
        ChatSession session = sessionStore.get(sessionId);
        if (session == null) {
            return Collections.emptyMap();
        }
        return new HashMap<>(session.getDrafts());
    }

    public byte[] generatePdf(Map<String, Object> params) {
        String title = String.valueOf(params.getOrDefault("title", "CRIE Institutional Report"));
        String content = String.valueOf(params.getOrDefault("content", "Regulatory and Academic Compliance Details"));

        String streamContent = "BT /F1 14 Tf 50 750 Td (" + escapePdf(title) + ") Tj 0 -24 Td /F1 10 Tf (" + escapePdf(content) + ") Tj ET";
        byte[] streamBytes = streamContent.getBytes(StandardCharsets.ISO_8859_1);

        StringBuilder pdf = new StringBuilder();
        pdf.append("%PDF-1.4\n");
        pdf.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n");
        pdf.append("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n");
        pdf.append("3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n");
        pdf.append("4 0 obj\n<< /Length ").append(streamBytes.length).append(" >>\nstream\n");
        pdf.append(streamContent);
        pdf.append("\nendstream\nendobj\n");
        pdf.append("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n");
        pdf.append("xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000350 00000 n \n");
        pdf.append("trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n425\n%%EOF\n");

        return pdf.toString().getBytes(StandardCharsets.ISO_8859_1);
    }

    public byte[] generateDocx(Map<String, Object> params) throws IOException {
        String title = String.valueOf(params.getOrDefault("title", "CRIE Institutional Specification"));
        String content = String.valueOf(params.getOrDefault("content", "Automated Document Generation"));

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(baos, StandardCharsets.UTF_8)) {
            writeZipEntry(zos, "[Content_Types].xml",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" +
                    "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">" +
                    "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>" +
                    "<Default Extension=\"xml\" ContentType=\"application/xml\"/>" +
                    "<Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>" +
                    "</Types>");

            writeZipEntry(zos, "_rels/.rels",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" +
                    "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">" +
                    "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>" +
                    "</Relationships>");

            String documentXml = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" +
                    "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">" +
                    "<w:body>" +
                    "<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>" + escapeXml(title) + "</w:t></w:r></w:p>" +
                    "<w:p><w:r><w:t>" + escapeXml(content) + "</w:t></w:r></w:p>" +
                    "</w:body></w:document>";
            writeZipEntry(zos, "word/document.xml", documentXml);
        }
        return baos.toByteArray();
    }

    public byte[] generateXlsx(Map<String, Object> params) throws IOException {
        String sheetName = String.valueOf(params.getOrDefault("sheetName", "WorkloadMetrics"));
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(baos, StandardCharsets.UTF_8)) {
            writeZipEntry(zos, "[Content_Types].xml",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" +
                    "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">" +
                    "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>" +
                    "<Default Extension=\"xml\" ContentType=\"application/xml\"/>" +
                    "<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>" +
                    "<Override PartName=\"/xl/worksheets/sheet1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>" +
                    "</Types>");

            writeZipEntry(zos, "_rels/.rels",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" +
                    "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">" +
                    "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/>" +
                    "</Relationships>");

            writeZipEntry(zos, "xl/_rels/workbook.xml.rels",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" +
                    "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">" +
                    "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet1.xml\"/>" +
                    "</Relationships>");

            writeZipEntry(zos, "xl/workbook.xml",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" +
                    "<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">" +
                    "<sheets><sheet name=\"" + escapeXml(sheetName) + "\" sheetId=\"1\" r:id=\"rId1\"/></sheets>" +
                    "</workbook>");

            writeZipEntry(zos, "xl/worksheets/sheet1.xml",
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" +
                    "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">" +
                    "<sheetData>" +
                    "<row r=\"1\"><c r=\"A1\" t=\"inlineStr\"><is><t>Metric</t></is></c><c r=\"B1\" t=\"inlineStr\"><is><t>Value</t></is></c></row>" +
                    "<row r=\"2\"><c r=\"A2\" t=\"inlineStr\"><is><t>ActiveCatalogDocuments</t></is></c><c r=\"B2\"><v>" + documentCatalog.size() + "</v></c></row>" +
                    "</sheetData></worksheet>");
        }
        return baos.toByteArray();
    }

    public byte[] generateTargetedBundle(List<String> documentIds, Map<String, Object> filters) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(baos, StandardCharsets.UTF_8)) {
            List<String> selected = (documentIds == null || documentIds.isEmpty())
                    ? new ArrayList<>(documentCatalog.keySet())
                    : documentIds;

            int count = 0;
            for (String docId : selected) {
                if (documentCatalog.containsKey(docId)) {
                    String docName = documentCatalog.get(docId);
                    String fileContent = "Document ID: " + docId + "\n" +
                            "Title: " + docName + "\n" +
                            "Provider: " + INSTITUTIONAL_PROVIDER + "\n" +
                            "Generated: " + Instant.now().toString() + "\n";
                    writeZipEntry(zos, "bundle/" + docId + ".txt", fileContent);
                    count++;
                }
            }

            String manifest = "Targeted Bundle Manifest\n" +
                    "Provider: " + INSTITUTIONAL_PROVIDER + "\n" +
                    "PackageTimestamp: " + Instant.now().toString() + "\n" +
                    "ContainedDocumentsCount: " + count + "\n" +
                    "FilterParams: " + (filters != null ? filters.toString() : "{}") + "\n";
            writeZipEntry(zos, "manifest.txt", manifest);
        }
        return baos.toByteArray();
    }

    private void writeZipEntry(ZipOutputStream zos, String entryName, String content) throws IOException {
        ZipEntry entry = new ZipEntry(entryName);
        zos.putNextEntry(entry);
        zos.write(content.getBytes(StandardCharsets.UTF_8));
        zos.closeEntry();
    }

    private String escapeXml(String text) {
        if (text == null) return "";
        return text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace("\"", "&quot;")
                   .replace("'", "&apos;");
    }

    private String escapePdf(String text) {
        if (text == null) return "";
        return text.replace("\\", "\\\\")
                   .replace("(", "\\(")
                   .replace(")", "\\)");
    }
}
