package com.eneik.crie.services;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;

/**
 * Internal service handling examination session schedule generation and document lifecycle.
 * Supports GOST R 7.0.97-2016 compliant DOCX generation for target academic groups and postgraduates.
 */
@Service
public class InternalService {

    private static final Logger log = LoggerFactory.getLogger(InternalService.class);

    public static final String DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    public static final String GOST_STANDARD = "ГОСТ Р 7.0.97-2016";
    public static final String DEFAULT_SESSION_PERIOD = "25.01 - 25.02";

    public static final Set<String> SUPPORTED_GROUPS = Set.of(
            "25ОЭ", "26ОЭ",
            "25ОИ", "26ОИ",
            "25ОП", "26ОП",
            "АСПИРАНТУРА", "POSTGRADUATE"
    );

    @Value("${crie.download.dir:data/downloads}")
    private String downloadDir = "data/downloads";

    public static class ScheduleRecord {
        private final String groupCode;
        private final String discipline;
        private final String examDate;
        private final String time;
        private final String classroom;
        private final String lecturer;

        public ScheduleRecord(String groupCode, String discipline, String examDate, String time, String classroom, String lecturer) {
            this.groupCode = groupCode;
            this.discipline = discipline;
            this.examDate = examDate;
            this.time = time;
            this.classroom = classroom;
            this.lecturer = lecturer;
        }

        public String getGroupCode() { return groupCode; }
        public String getDiscipline() { return discipline; }
        public String getExamDate() { return examDate; }
        public String getTime() { return time; }
        public String getClassroom() { return classroom; }
        public String getLecturer() { return lecturer; }
    }

    public static class GenerationResult {
        private final String fileName;
        private final Path filePath;
        private final byte[] content;
        private final String mimeType;
        private final List<String> groups;
        private final String period;

        public GenerationResult(String fileName, Path filePath, byte[] content, String mimeType, List<String> groups, String period) {
            this.fileName = fileName;
            this.filePath = filePath;
            this.content = content;
            this.mimeType = mimeType;
            this.groups = groups;
            this.period = period;
        }

        public String getFileName() { return fileName; }
        public Path getFilePath() { return filePath; }
        public byte[] getContent() { return content; }
        public String getMimeType() { return mimeType; }
        public List<String> getGroups() { return groups; }
        public String getPeriod() { return period; }
    }

    /**
     * Generate an official examination schedule document complying with GOST R 7.0.97-2016.
     */
    public GenerationResult generateExaminationSchedule(List<String> requestedGroups, String sessionPeriod) throws IOException {
        List<String> targetGroups = (requestedGroups == null || requestedGroups.isEmpty())
                ? new ArrayList<>(SUPPORTED_GROUPS)
                : requestedGroups.stream().filter(SUPPORTED_GROUPS::contains).toList();

        if (targetGroups.isEmpty()) {
            throw new IllegalArgumentException("No valid supported groups specified for examination schedule generation.");
        }

        String period = (sessionPeriod != null && !sessionPeriod.isBlank()) ? sessionPeriod : DEFAULT_SESSION_PERIOD;
        List<ScheduleRecord> records = buildDefaultScheduleRecords(targetGroups);

        byte[] docxBytes = buildDocxPackage(targetGroups, period, records);

        Path targetDir = Paths.get(downloadDir);
        if (!Files.exists(targetDir)) {
            Files.createDirectories(targetDir);
        }

        String fileName = String.format("examination_schedule_%s_%s.docx",
                period.replace(" ", "").replace(".", "_").replace("-", "_"),
                UUID.randomUUID().toString().substring(0, 8));
        Path savedFile = targetDir.resolve(fileName);
        Files.write(savedFile, docxBytes);
        log.info("Generated GOST-compliant examination schedule at {}", savedFile);

        return new GenerationResult(fileName, savedFile, docxBytes, DOCX_MIME_TYPE, targetGroups, period);
    }

    /**
     * Validates that the provided byte array constitutes a valid OpenXML DOCX archive.
     */
    public boolean validateDocumentIntegrity(byte[] docxBytes) {
        if (docxBytes == null || docxBytes.length < 100) {
            return false;
        }
        Set<String> requiredEntries = Set.of(
                "[Content_Types].xml",
                "_rels/.rels",
                "word/document.xml"
        );
        Set<String> foundEntries = new HashSet<>();
        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(docxBytes))) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                foundEntries.add(entry.getName());
            }
        } catch (IOException e) {
            log.error("Document integrity verification failed", e);
            return false;
        }
        return foundEntries.containsAll(requiredEntries);
    }

    private List<ScheduleRecord> buildDefaultScheduleRecords(List<String> groups) {
        List<ScheduleRecord> records = new ArrayList<>();
        Map<String, String[]> groupCurriculum = Map.of(
                "25ОЭ", new String[]{"Микроэкономика", "Финансовый анализ", "Статистика"},
                "26ОЭ", new String[]{"Макроэкономика", "Корпоративные финансы", "Эконометрика"},
                "25ОИ", new String[]{"Алгоритмы и структуры данных", "Архитектура ЭВМ", "Базы данных"},
                "26ОИ", new String[]{"Распределенные системы", "Машинное обучение", "Информационная безопасность"},
                "25ОП", new String[]{"Теория государства и права", "Гражданское право", "Конституционное право"},
                "26ОП", new String[]{"Уголовное право", "Административное право", "Международное право"},
                "АСПИРАНТУРА", new String[]{"История и философия науки", "Иностранный язык (специальный)", "Специальная дисциплина"}
        );

        for (String group : groups) {
            String[] disciplines = groupCurriculum.getOrDefault(group, new String[]{"Научно-исследовательская работа", "Государственная аттестация"});
            int dayOffset = 25;
            for (String disc : disciplines) {
                String dateStr = String.format("%02d.01.2026", dayOffset);
                records.add(new ScheduleRecord(group, disc, dateStr, "09:00", "Ауд. 402-А", "Проф. Иванов И.И."));
                dayOffset += 4;
            }
        }
        return records;
    }

    private byte[] buildDocxPackage(List<String> groups, String period, List<ScheduleRecord> records) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(baos, StandardCharsets.UTF_8)) {
            writeEntry(zos, "[Content_Types].xml", buildContentTypesXml());
            writeEntry(zos, "_rels/.rels", buildGlobalRelsXml());
            writeEntry(zos, "word/_rels/document.xml.rels", buildWordRelsXml());
            writeEntry(zos, "word/document.xml", buildDocumentXml(groups, period, records));
        }
        return baos.toByteArray();
    }

    private void writeEntry(ZipOutputStream zos, String path, String content) throws IOException {
        ZipEntry entry = new ZipEntry(path);
        zos.putNextEntry(entry);
        zos.write(content.getBytes(StandardCharsets.UTF_8));
        zos.closeEntry();
    }

    private String buildContentTypesXml() {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n" +
                "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">\n" +
                "  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>\n" +
                "  <Default Extension=\"xml\" ContentType=\"application/xml\"/>\n" +
                "  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>\n" +
                "</Types>";
    }

    private String buildGlobalRelsXml() {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n" +
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n" +
                "  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>\n" +
                "</Relationships>";
    }

    private String buildWordRelsXml() {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n" +
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"/>";
    }

    private String buildDocumentXml(List<String> groups, String period, List<ScheduleRecord> records) {
        StringBuilder sb = new StringBuilder();
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n");
        sb.append("<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">\n");
        sb.append("  <w:body>\n");

        // Title compliant with GOST R 7.0.97-2016
        sb.append("    <w:p><w:pPr><w:jc w:val=\"center\"/></w:pPr><w:r><w:rPr><w:b/><w:sz w:val=\"28\"/></w:rPr><w:t>РАСПИСАНИЕ ЭКЗАМЕНАЦИОННОЙ СЕССИИ</w:t></w:r></w:p>\n");
        sb.append("    <w:p><w:pPr><w:jc w:val=\"center\"/></w:pPr><w:r><w:rPr><w:i/><w:sz w:val=\"24\"/></w:rPr><w:t>Период сессии: ").append(period).append(" (соответствие ").append(GOST_STANDARD).append(")</w:t></w:r></w:p>\n");
        sb.append("    <w:p><w:pPr><w:jc w:val=\"center\"/></w:pPr><w:r><w:rPr><w:sz w:val=\"22\"/></w:rPr><w:t>Группы: ").append(String.join(", ", groups)).append("</w:t></w:r></w:p>\n");
        sb.append("    <w:p/>\n");

        // Schedule Table
        sb.append("    <w:tbl>\n");
        sb.append("      <w:tblPr><w:tblBorders><w:top w:val=\"single\" w:sz=\"4\"/><w:bottom w:val=\"single\" w:sz=\"4\"/><w:insideH w:val=\"single\" w:sz=\"4\"/><w:insideV w:val=\"single\" w:sz=\"4\"/></w:tblBorders></w:tblPr>\n");

        // Table Header
        sb.append("      <w:tr>\n");
        appendTableCell(sb, "Группа", true);
        appendTableCell(sb, "Дисциплина", true);
        appendTableCell(sb, "Дата", true);
        appendTableCell(sb, "Время", true);
        appendTableCell(sb, "Аудитория", true);
        appendTableCell(sb, "Преподаватель", true);
        sb.append("      </w:tr>\n");

        // Table Data
        for (ScheduleRecord r : records) {
            sb.append("      <w:tr>\n");
            appendTableCell(sb, r.getGroupCode(), false);
            appendTableCell(sb, r.getDiscipline(), false);
            appendTableCell(sb, r.getExamDate(), false);
            appendTableCell(sb, r.getTime(), false);
            appendTableCell(sb, r.getClassroom(), false);
            appendTableCell(sb, r.getLecturer(), false);
            sb.append("      </w:tr>\n");
        }

        sb.append("    </w:tbl>\n");
        sb.append("    <w:sectPr><w:pgMar w:top=\"1134\" w:right=\"567\" w:bottom=\"1134\" w:left=\"1701\"/></w:sectPr>\n"); // Left margin 30mm, right 10mm, top/bottom 20mm per GOST
        sb.append("  </w:body>\n");
        sb.append("</w:document>");
        return sb.toString();
    }

    private void appendTableCell(StringBuilder sb, String text, boolean isHeader) {
        sb.append("        <w:tc><w:p><w:r><w:rPr>");
        if (isHeader) {
            sb.append("<w:b/>");
        }
        sb.append("<w:sz w:val=\"20\"/></w:rPr><w:t>");
        sb.append(escapeXml(text));
        sb.append("</w:t></w:r></w:p></w:tc>\n");
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
