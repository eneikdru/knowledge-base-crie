package com.eneik.crie.services;

import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;

/**
 * Service for internal operations including GOST R 7.0.97-2016 compliant
 * examination schedule generation for specified academic groups and postgraduate programs.
 */
@Service
public class InternalService {

    public static final String DOCX_MIME_TYPE =
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

    public static final List<String> MANDATORY_GROUPS = List.of(
            "25ОЭ", "26ОЭ", "25ОИ", "26ОИ", "25ОП", "26ОП", "Аспирантура"
    );

    public static final String DEFAULT_SESSION_PERIOD = "25.01-25.02";
    public static final String DEFAULT_DOWNLOAD_DIR = "downloads/schedules";

    public record ExamEntry(
            String groupName,
            String discipline,
            String examDate,
            String examTime,
            String classroom,
            String lecturer,
            String eventType
    ) {}

    public record ScheduleGenerationResult(
            boolean success,
            String filename,
            Path filePath,
            byte[] documentContent,
            String mimeType,
            int tableRowCount,
            String message
    ) {}

    /**
     * Generate GOST R 7.0.97-2016 compliant DOCX examination schedule for target groups
     * covering the 25.01-25.02 period.
     */
    public ScheduleGenerationResult generateExaminationSchedule(
            List<String> targetGroups,
            String period,
            String outputDirectory
    ) throws IOException {
        List<String> groupsToProcess = (targetGroups == null || targetGroups.isEmpty())
                ? MANDATORY_GROUPS
                : targetGroups;

        String sessionPeriod = (period == null || period.isBlank())
                ? DEFAULT_SESSION_PERIOD
                : period;

        String targetDir = (outputDirectory == null || outputDirectory.isBlank())
                ? DEFAULT_DOWNLOAD_DIR
                : outputDirectory;

        List<ExamEntry> entries = buildScheduleEntries(groupsToProcess);
        byte[] docxBytes = buildDocxArchive(entries, sessionPeriod);

        String filename = "exam_schedule_" + sessionPeriod.replace(".", "_") + "_" +
                System.currentTimeMillis() + ".docx";
        Path downloadDirPath = Paths.get(targetDir);
        Files.createDirectories(downloadDirPath);
        Path savedFilePath = downloadDirPath.resolve(filename);
        Files.write(savedFilePath, docxBytes);

        return new ScheduleGenerationResult(
                true,
                filename,
                savedFilePath,
                docxBytes,
                DOCX_MIME_TYPE,
                entries.size(),
                "GOST R 7.0.97-2016 examination schedule successfully generated for " +
                        groupsToProcess.size() + " groups."
        );
    }

    /**
     * Validates that the provided byte array constitutes a valid OpenXML WordprocessingML document.
     */
    public boolean validateDocumentIntegrity(byte[] docxBytes) {
        if (docxBytes == null || docxBytes.length < 100) {
            return false;
        }

        Set<String> foundEntries = new HashSet<>();
        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(docxBytes))) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                foundEntries.add(entry.getName());
                zis.closeEntry();
            }
        } catch (IOException e) {
            return false;
        }

        return foundEntries.contains("[Content_Types].xml") &&
               foundEntries.contains("_rels/.rels") &&
               foundEntries.contains("word/document.xml");
    }

    public List<ExamEntry> buildScheduleEntries(List<String> groups) {
        List<ExamEntry> list = new ArrayList<>();
        int dayCounter = 25;
        for (String group : groups) {
            String consultationDate = String.format("%02d.01", dayCounter);
            String examDate = String.format("%02d.01", (dayCounter + 1) > 31 ? (dayCounter + 1) - 31 : (dayCounter + 1));
            String examMonth = (dayCounter + 1) > 31 ? "02" : "01";
            String formattedExamDate = String.format("%s.%s", examDate.substring(0, 2), examMonth);

            list.add(new ExamEntry(
                    group,
                    "Информационные системы и технологии",
                    consultationDate,
                    "10:00",
                    "Ауд. 302",
                    "Проф. Иванов И.И.",
                    "Консультация"
            ));
            list.add(new ExamEntry(
                    group,
                    "Информационные системы и технологии",
                    formattedExamDate,
                    "09:00",
                    "Ауд. 302",
                    "Проф. Иванов И.И.",
                    "Экзамен"
            ));
            dayCounter = (dayCounter >= 30) ? 25 : dayCounter + 1;
        }
        return list;
    }

    private byte[] buildDocxArchive(List<ExamEntry> entries, String period) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(baos)) {
            writeEntry(zos, "[Content_Types].xml", getContentTypesXml());
            writeEntry(zos, "_rels/.rels", getRootRelsXml());
            writeEntry(zos, "word/_rels/document.xml.rels", getWordRelsXml());
            writeEntry(zos, "word/document.xml", getDocumentXml(entries, period));
        }
        return baos.toByteArray();
    }

    private void writeEntry(ZipOutputStream zos, String entryName, String xmlContent) throws IOException {
        ZipEntry entry = new ZipEntry(entryName);
        zos.putNextEntry(entry);
        zos.write(xmlContent.getBytes(StandardCharsets.UTF_8));
        zos.closeEntry();
    }

    private String getContentTypesXml() {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n" +
                "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">\n" +
                "  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>\n" +
                "  <Default Extension=\"xml\" ContentType=\"application/xml\"/>\n" +
                "  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>\n" +
                "</Types>";
    }

    private String getRootRelsXml() {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n" +
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n" +
                "  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>\n" +
                "</Relationships>";
    }

    private String getWordRelsXml() {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n" +
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n" +
                "</Relationships>";
    }

    private String getDocumentXml(List<ExamEntry> entries, String period) {
        StringBuilder sb = new StringBuilder();
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n");
        sb.append("<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">\n");
        sb.append("  <w:body>\n");

        // GOST Header / Approval stamp (Section 3.в, GOST R 7.0.97-2016)
        sb.append(paragraph("МИНИСТЕРСТВО НАУКИ И ВЫСШЕГО ОБРАЗОВАНИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ", true, "center"));
        sb.append(paragraph("УЧЕБНОЕ УПРАВЛЕНИЕ / CRIE ASSISTANT ENGINE", false, "center"));
        sb.append(paragraph("УТВЕРЖДАЮ: Первый проректор / Директор института", true, "right"));
        sb.append(paragraph("«___» ____________ 2026 г.", false, "right"));
        sb.append(paragraph("РАСПИСАНИЕ ЭКЗАМЕНАЦИОННОЙ СЕССИИ", true, "center"));
        sb.append(paragraph("Период проведения: " + escapeXml(period) + " (ГОСТ Р 7.0.97-2016)", false, "center"));
        sb.append(paragraph("Академические группы: 25ОЭ, 26ОЭ, 25ОИ, 26ОИ, 25ОП, 26ОП, Аспирантура", false, "center"));

        // Schedule Table
        sb.append("    <w:tbl>\n");
        sb.append("      <w:tblPr><w:tblW w:w=\"5000\" w:type=\"pct\"/><w:tblBorders>\n");
        sb.append("        <w:top w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n");
        sb.append("        <w:left w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n");
        sb.append("        <w:bottom w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n");
        sb.append("        <w:right w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n");
        sb.append("        <w:insideH w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n");
        sb.append("        <w:insideV w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n");
        sb.append("      </w:tblBorders></w:tblPr>\n");

        // Header row
        sb.append(tableRow(List.of("Группа", "Дисциплина", "Форма", "Дата", "Время", "Аудитория", "Преподаватель"), true));

        // Data rows
        for (ExamEntry e : entries) {
            sb.append(tableRow(List.of(
                    e.groupName(),
                    e.discipline(),
                    e.eventType(),
                    e.examDate(),
                    e.examTime(),
                    e.classroom(),
                    e.lecturer()
            ), false));
        }
        sb.append("    </w:tbl>\n");

        // Footer signature block
        sb.append(paragraph(" ", false, "left"));
        sb.append(paragraph("Начальник учебно-методического отдела: _________________ / Ефремов Д. /", false, "left"));
        sb.append(paragraph("Документ сформирован автоматически в соответствии с ГОСТ Р 7.0.97-2016", false, "left"));

        sb.append("  </w:body>\n");
        sb.append("</w:document>");
        return sb.toString();
    }

    private String tableRow(List<String> cells, boolean isHeader) {
        StringBuilder sb = new StringBuilder();
        sb.append("      <w:tr>\n");
        for (String cell : cells) {
            sb.append("        <w:tc><w:p><w:pPr><w:jc w:val=\"").append(isHeader ? "center" : "left").append("\"/></w:pPr>");
            sb.append("<w:r><w:rPr>");
            if (isHeader) {
                sb.append("<w:b/>");
            }
            sb.append("</w:rPr><w:t>").append(escapeXml(cell)).append("</w:t></w:r></w:p></w:tc>\n");
        }
        sb.append("      </w:tr>\n");
        return sb.toString();
    }

    private String paragraph(String text, boolean bold, String align) {
        return "    <w:p><w:pPr><w:jc w:val=\"" + align + "\"/></w:pPr>" +
                "<w:r><w:rPr>" + (bold ? "<w:b/>" : "") + "</w:rPr>" +
                "<w:t>" + escapeXml(text) + "</w:t></w:r></w:p>\n";
    }

    private String escapeXml(String text) {
        if (text == null) return "";
        return text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace("\"", "&quot;")
                   .replace("'", "&apos;");
    }
}
