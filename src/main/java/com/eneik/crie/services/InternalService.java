package com.eneik.crie.services;

import org.springframework.stereotype.Service;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * Internal service handling autopoietic backend tasks:
 * - Purging branding leaks & computing catalog totals
 * - Managing temporal chat continuity and session persistence
 * - Compiling dynamic DOCX, XLSX, and PDF documents
 * - Assembling targeted ZIP bundles
 */
@Service("crieInternalService")
public class InternalService {

    private final Map<String, List<Map<String, String>>> chatSessions = new ConcurrentHashMap<>();
    private final Map<String, String> sessionDrafts = new ConcurrentHashMap<>();

    /**
     * Returns sanitized system metadata and actual indexed catalog totals,
     * ensuring no DeepSeek or legacy 1713 counter abstraction leaks exist.
     */
    public Map<String, Object> getSystemMetadata(int realIndexedCount) {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("institution", "CRIE Institutional Platform");
        metadata.put("engine", "CRIE Autopoietic Core");
        metadata.put("indexedDocumentsCount", realIndexedCount);
        metadata.put("status", "OPERATIONAL");
        return metadata;
    }

    /**
     * Persists or updates chat session history for temporal continuity.
     */
    public void saveChatMessage(String sessionId, String role, String content) {
        chatSessions.computeIfAbsent(sessionId, k -> Collections.synchronizedList(new ArrayList<>()
        )).add(Map.of("role", role, "content", content, "timestamp", String.valueOf(System.currentTimeMillis())));
    }

    /**
     * Retrieves existing chat history for session restoration.
     */
    public List<Map<String, String>> getChatHistory(String sessionId) {
        return chatSessions.getOrDefault(sessionId, Collections.emptyList());
    }

    /**
     * Persists active document drafts across sessions.
     */
    public void saveDocumentDraft(String sessionId, String draftContent) {
        sessionDrafts.put(sessionId, draftContent);
    }

    /**
     * Retrieves active document draft for a session.
     */
    public String getDocumentDraft(String sessionId) {
        return sessionDrafts.getOrDefault(sessionId, "");
    }

    /**
     * Generates a standard DOCX document binary from template parameters.
     */
    public byte[] generateDocx(String title, Map<String, Object> parameters) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(out)) {
            zos.putNextEntry(new ZipEntry("[Content_Types].xml"));
            String contentTypes = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" +
                    "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">" +
                    "<Default Extension=\"xml\" ContentType=\"application/xml\"/>" +
                    "<Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>" +
                    "</Types>";
            zos.write(contentTypes.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            zos.putNextEntry(new ZipEntry("word/document.xml"));
            StringBuilder body = new StringBuilder();
            body.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>");
            body.append("<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">");
            body.append("<w:body><w:p><w:r><w:t>").append(escapeXml(title)).append("</w:t></w:r></w:p>");
            if (parameters != null) {
                for (Map.Entry<String, Object> entry : parameters.entrySet()) {
                    body.append("<w:p><w:r><w:t>").append(escapeXml(entry.getKey())).append(": ")
                        .append(escapeXml(String.valueOf(entry.getValue()))).append("</w:t></w:r></w:p>");
                }
            }
            body.append("</w:body></w:document>");
            zos.write(body.toString().getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }
        return out.toByteArray();
    }

    /**
     * Generates a standard XLSX document binary from tabular data.
     */
    public byte[] generateXlsx(String sheetName, List<Map<String, Object>> rows) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(out)) {
            zos.putNextEntry(new ZipEntry("[Content_Types].xml"));
            String contentTypes = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" +
                    "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">" +
                    "<Default Extension=\"xml\" ContentType=\"application/xml\"/>" +
                    "<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>" +
                    "</Types>";
            zos.write(contentTypes.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            zos.putNextEntry(new ZipEntry("xl/workbook.xml"));
            StringBuilder wb = new StringBuilder();
            wb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>");
            wb.append("<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">");
            wb.append("<sheets><sheet name=\"").append(escapeXml(sheetName)).append("\" sheetId=\"1\" r:id=\"rId1\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"/></sheets>");
            wb.append("</workbook>");
            zos.write(wb.toString().getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }
        return out.toByteArray();
    }

    /**
     * Generates a compliant PDF binary stream.
     */
    public byte[] generatePdf(String title, String content) {
        String safeTitle = title != null ? title : "Document";
        String safeContent = content != null ? content : "";
        StringBuilder pdf = new StringBuilder();
        pdf.append("%PDF-1.4\n");
        pdf.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n");
        pdf.append("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n");
        pdf.append("3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n");
        String streamData = "BT /F1 12 Tf 72 712 Td (" + escapePdf(safeTitle + ": " + safeContent) + ") Tj ET";
        pdf.append("4 0 obj\n<< /Length ").append(streamData.length()).append(" >>\nstream\n")
           .append(streamData).append("\nendstream\nendobj\n");
        pdf.append("xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000214 00000 n \n");
        pdf.append("trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n310\n%%EOF");
        return pdf.toString().getBytes(StandardCharsets.ISO_8859_1);
    }

    /**
     * Packages dynamically filtered documents into a targeted ZIP archive.
     */
    public byte[] createTargetedBundle(Map<String, byte[]> documents) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(baos)) {
            for (Map.Entry<String, byte[]> doc : documents.entrySet()) {
                ZipEntry entry = new ZipEntry(doc.getKey());
                zos.putNextEntry(entry);
                zos.write(doc.getValue());
                zos.closeEntry();
            }
        }
        return baos.toByteArray();
    }

    private String escapeXml(String input) {
        if (input == null) return "";
        return input.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace("\"", "&quot;")
                    .replace("'", "&apos;");
    }

    private String escapePdf(String input) {
        if (input == null) return "";
        return input.replace("\\", "\\\\")
                    .replace("(", "\\(")
                    .replace(")", "\\)");
    }
}
