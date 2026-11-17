package com.eneik.crie.services;

import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * Internal service handling GOST R 7.0.97-2016 compliant examination schedule document generation
 * for academic groups 25ОЭ, 26ОЭ, 25ОИ, 26ОИ, 25ОП, 26ОП and postgraduate students.
 */
@Service
public class InternalService {

    public static final List<String> MANDATORY_GROUPS = Collections.unmodifiableList(
            Arrays.asList("25ОЭ", "26ОЭ", "25ОИ", "26ОИ", "25ОП", "26ОП", "Аспирантура (Postgraduate)")
    );

    public static final String DEFAULT_PERIOD_START = "25.01";
    public static final String DEFAULT_PERIOD_END = "25.02";
    public static final String GOST_STANDARD_ID = "ГОСТ Р 7.0.97-2016";
    public static final String DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

    private final Path downloadDirectory;

    public InternalService() {
        this(Paths.get(System.getProperty("java.io.tmpdir"), "crie-downloads"));
    }

    public InternalService(Path downloadDirectory) {
        this.downloadDirectory = downloadDirectory;
        try {
            Files.createDirectories(this.downloadDirectory);
        } catch (IOException ignored) {
            // Directory creation fallback handled at runtime
        }
    }

    public Path getDownloadDirectory() {
        return downloadDirectory;
    }

    /**
     * Represents an examination item entry in the schedule.
     */
    public static class ExamScheduleItem {
        private final String group;
        private final String discipline;
        private final String examDate;
        private final String examTime;
        private final String classroom;
        private final String examiner;
        private final String consultationDate;

        public ExamScheduleItem(String group, String discipline, String examDate, String examTime, String classroom, String examiner, String consultationDate) {
            this.group = group;
            this.discipline = discipline;
            this.examDate = examDate;
            this.examTime = examTime;
            this.classroom = classroom;
            this.examiner = examiner;
            this.consultationDate = consultationDate;
        }

        public String getGroup() { return group; }
        public String getDiscipline() { return discipline; }
        public String getExamDate() { return examDate; }
        public String getExamTime() { return examTime; }
        public String getClassroom() { return classroom; }
        public String getExaminer() { return examiner; }
        public String getConsultationDate() { return consultationDate; }
    }

    /**
     * Generates a sample schedule conforming to default groups and the 25.01 - 25.02 session window.
     */
    public List<ExamScheduleItem> createDefaultScheduleItems(int academicYear) {
        List<ExamScheduleItem> items = new ArrayList<>();
        String yr = String.valueOf(academicYear);

        items.add(new ExamScheduleItem("25ОЭ", "Экономика предприятия и анализ", "28.01." + yr, "09:00", "Ауд. 402", "доц. Смирнов А.В.", "26.01." + yr + " 11:00"));
        items.add(new ExamScheduleItem("25ОЭ", "Финансовый менеджмент", "08.02." + yr, "10:00", "Ауд. 405", "проф. Морозов В.П.", "06.02." + yr + " 12:00"));

        items.add(new ExamScheduleItem("26ОЭ", "Бухгалтерский учет и аудит", "30.01." + yr, "09:30", "Ауд. 410", "доц. Ковалева Е.Н.", "28.01." + yr + " 13:00"));
        items.add(new ExamScheduleItem("26ОЭ", "Микроэкономический анализ", "12.02." + yr, "11:00", "Ауд. 408", "доц. Волков С.М.", "10.02." + yr + " 14:00"));

        items.add(new ExamScheduleItem("25ОИ", "Архитектура вычислительных систем", "29.01." + yr, "09:00", "Лаб. 214", "проф. Иванов И.И.", "27.01." + yr + " 10:00"));
        items.add(new ExamScheduleItem("25ОИ", "Интеллектуальные информационные системы", "10.02." + yr, "10:30", "Лаб. 218", "доц. Петров П.С.", "08.02." + yr + " 12:00"));

        items.add(new ExamScheduleItem("26ОИ", "Проектирование баз данных", "01.02." + yr, "10:00", "Ауд. 312", "доц. Сидоров А.К.", "30.01." + yr + " 14:00"));
        items.add(new ExamScheduleItem("26ОИ", "Распределенные вычисления", "15.02." + yr, "12:00", "Ауд. 316", "проф. Васильев Н.Г.", "13.02." + yr + " 15:00"));

        items.add(new ExamScheduleItem("25ОП", "Методология программной инженерии", "02.02." + yr, "09:00", "Лаб. 105", "доц. Кузнецов Д.А.", "31.01." + yr + " 11:30"));
        items.add(new ExamScheduleItem("25ОП", "Верификация программного обеспечения", "17.02." + yr, "10:00", "Лаб. 107", "проф. Николаев Б.В.", "15.02." + yr + " 11:00"));

        items.add(new ExamScheduleItem("26ОП", "Технологии командной разработки ПО", "04.02." + yr, "11:00", "Ауд. 202", "доц. Григорьев М.Ю.", "02.02." + yr + " 13:00"));
        items.add(new ExamScheduleItem("26ОП", "Архитектура веб-ориентированных комплексов", "19.02." + yr, "09:00", "Ауд. 206", "доц. Лебедев О.Н.", "17.02." + yr + " 14:00"));

        items.add(new ExamScheduleItem("Аспирантура (Postgraduate)", "История и философия науки", "06.02." + yr, "14:00", "Конф-зал 1", "проф. Федоров А.М.", "04.02." + yr + " 15:00"));
        items.add(new ExamScheduleItem("Аспирантура (Postgraduate)", "Специальная дисциплина (09.06.01)", "22.02." + yr, "14:00", "Кафедра 12", "проф. Соколов В.Е.", "20.02." + yr + " 16:00"));

        return items;
    }

    /**
     * Generates a GOST R 7.0.97-2016 compliant DOCX file for groups 25ОЭ, 26ОЭ, 25ОИ, 26ОИ, 25ОП, 26ОП
     * and postgraduate students covering the session period 25.01 - 25.02.
     */
    public byte[] generateExaminationScheduleDocx(List<String> targetGroups, String periodStart, String periodEnd, int academicYear) throws IOException {
        List<String> groupsToInclude = (targetGroups == null || targetGroups.isEmpty()) ? MANDATORY_GROUPS : targetGroups;
        String start = (periodStart == null || periodStart.trim().isEmpty()) ? DEFAULT_PERIOD_START : periodStart;
        String end = (periodEnd == null || periodEnd.trim().isEmpty()) ? DEFAULT_PERIOD_END : periodEnd;

        List<ExamScheduleItem> allItems = createDefaultScheduleItems(academicYear);
        List<ExamScheduleItem> filteredItems = new ArrayList<>();
        for (ExamScheduleItem item : allItems) {
            if (groupsToInclude.contains(item.getGroup())) {
                filteredItems.add(item);
            }
        }

        return buildDocxZipArchive(filteredItems, groupsToInclude, start, end, academicYear);
    }

    /**
     * Generates and writes the DOCX schedule to the designated download directory.
     */
    public Path exportScheduleToDownloadDirectory(List<String> targetGroups, String periodStart, String periodEnd, int academicYear) throws IOException {
        byte[] docxBytes = generateExaminationScheduleDocx(targetGroups, periodStart, periodEnd, academicYear);
        String filename = String.format("examination_schedule_%s_%s_%d.docx",
                (periodStart != null ? periodStart : DEFAULT_PERIOD_START).replace('.', '_'),
                (periodEnd != null ? periodEnd : DEFAULT_PERIOD_END).replace('.', '_'),
                academicYear);

        Files.createDirectories(this.downloadDirectory);
        Path targetFile = this.downloadDirectory.resolve(filename);
        Files.write(targetFile, docxBytes);
        return targetFile;
    }

    /**
     * Builds a valid OpenXML WordProcessingML document archive (.docx).
     */
    private byte[] buildDocxZipArchive(List<ExamScheduleItem> items, List<String> groups, String periodStart, String periodEnd, int academicYear) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(baos, StandardCharsets.UTF_8)) {
            // 1. [Content_Types].xml
            writeZipEntry(zos, "[Content_Types].xml", getContentTypesXml());

            // 2. _rels/.rels
            writeZipEntry(zos, "_rels/.rels", getRootRelationshipsXml());

            // 3. word/_rels/document.xml.rels
            writeZipEntry(zos, "word/_rels/document.xml.rels", getWordRelationshipsXml());

            // 4. word/document.xml
            writeZipEntry(zos, "word/document.xml", getDocumentXml(items, groups, periodStart, periodEnd, academicYear));
        }
        return baos.toByteArray();
    }

    private void writeZipEntry(ZipOutputStream zos, String name, String xmlContent) throws IOException {
        ZipEntry entry = new ZipEntry(name);
        zos.putNextEntry(entry);
        byte[] data = xmlContent.getBytes(StandardCharsets.UTF_8);
        zos.write(data, 0, data.length);
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

    private String getContentTypesXml() {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n" +
                "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">\n" +
                "  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>\n" +
                "  <Default Extension=\"xml\" ContentType=\"application/xml\"/>\n" +
                "  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>\n" +
                "</Types>";
    }

    private String getRootRelationshipsXml() {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n" +
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n" +
                "  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>\n" +
                "</Relationships>";
    }

    private String getWordRelationshipsXml() {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n" +
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n" +
                "</Relationships>";
    }

    private String getDocumentXml(List<ExamScheduleItem> items, List<String> groups, String periodStart, String periodEnd, int academicYear) {
        StringBuilder sb = new StringBuilder();
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n");
        sb.append("<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">\n");
        sb.append("  <w:body>\n");

        // GOST R 7.0.97-2016 Approval Block (Реквизит 16 «Гриф утверждения документа»)
        sb.append("    <w:p>\n");
        sb.append("      <w:pPr><w:jc w:val=\"right\"/></w:pPr>\n");
        sb.append("      <w:r><w:rPr><w:b/><w:rFonts w:ascii=\"Times New Roman\" w:hAnsi=\"Times New Roman\"/><w:sz w:val=\"24\"/></w:rPr><w:t>УТВЕРЖДАЮ</w:t></w:r>\n");
        sb.append("    </w:p>\n");
        sb.append("    <w:p>\n");
        sb.append("      <w:pPr><w:jc w:val=\"right\"/></w:pPr>\n");
        sb.append("      <w:r><w:rPr><w:rFonts w:ascii=\"Times New Roman\" w:hAnsi=\"Times New Roman\"/><w:sz w:val=\"24\"/></w:rPr><w:t>Проректор по учебной работе</w:t></w:r>\n");
        sb.append("    </w:p>\n");
        sb.append("    <w:p>\n");
        sb.append("      <w:pPr><w:jc w:val=\"right\"/></w:pPr>\n");
        sb.append("      <w:r><w:rPr><w:rFonts w:ascii=\"Times New Roman\" w:hAnsi=\"Times New Roman\"/><w:sz w:val=\"24\"/></w:rPr><w:t>____________ / В.Н. Кузнецов /</w:t></w:r>\n");
        sb.append("    </w:p>\n");
        sb.append("    <w:p>\n");
        sb.append("      <w:pPr><w:jc w:val=\"right\"/></w:pPr>\n");
        sb.append("      <w:r><w:rPr><w:rFonts w:ascii=\"Times New Roman\" w:hAnsi=\"Times New Roman\"/><w:sz w:val=\"24\"/></w:rPr><w:t>«____» ____________ ").append(academicYear).append(" г.</w:t></w:r>\n");
        sb.append("    </w:p>\n");

        // Document Title
        sb.append("    <w:p>\n");
        sb.append("      <w:pPr><w:jc w:val=\"center\"/><w:spacing w:before=\"240\" w:after=\"120\"/></w:pPr>\n");
        sb.append("      <w:r><w:rPr><w:b/><w:rFonts w:ascii=\"Times New Roman\" w:hAnsi=\"Times New Roman\"/><w:sz w:val=\"28\"/></w:rPr><w:t>РАСПИСАНИЕ ЭКЗАМЕНАЦИОННОЙ СЕССИИ</w:t></w:r>\n");
        sb.append("    </w:p>\n");

        // Subheading with Period and Target Groups
        sb.append("    <w:p>\n");
        sb.append("      <w:pPr><w:jc w:val=\"center\"/><w:spacing w:after=\"240\"/></w:pPr>\n");
        sb.append("      <w:r><w:rPr><w:i/><w:rFonts w:ascii=\"Times New Roman\" w:hAnsi=\"Times New Roman\"/><w:sz w:val=\"24\"/></w:rPr><w:t>");
        sb.append("Период проведения экзаменационной сессии: с ").append(escapeXml(periodStart)).append(" по ").append(escapeXml(periodEnd)).append(" ").append(academicYear).append(" г.");
        sb.append("</w:t></w:r>\n");
        sb.append("    </w:p>\n");

        // Standard Conformity Notice (ГОСТ Р 7.0.97-2016)
        sb.append("    <w:p>\n");
        sb.append("      <w:pPr><w:jc w:val=\"center\"/><w:spacing w:after=\"240\"/></w:pPr>\n");
        sb.append("      <w:r><w:rPr><w:rFonts w:ascii=\"Times New Roman\" w:hAnsi=\"Times New Roman\"/><w:sz w:val=\"20\"/><w:color w:val=\"555555\"/></w:rPr><w:t>");
        sb.append("Документ сформирован в соответствии с требованиями ").append(GOST_STANDARD_ID);
        sb.append(" для учебных групп: ").append(escapeXml(String.join(", ", groups)));
        sb.append("</w:t></w:r>\n");
        sb.append("    </w:p>\n");

        // Schedule Table
        sb.append("    <w:tbl>\n");
        sb.append("      <w:tblPr>\n");
        sb.append("        <w:tblW w:w=\"9000\" w:type=\"dxa\"/>\n");
        sb.append("        <w:jc w:val=\"center\"/>\n");
        sb.append("        <w:tblBorders>\n");
        sb.append("          <w:top w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n");
        sb.append("          <w:left w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n");
        sb.append("          <w:bottom w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n");
        sb.append("          <w:right w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n");
        sb.append("          <w:insideH w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n");
        sb.append("          <w:insideV w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>\n");
        sb.append("        </w:tblBorders>\n");
        sb.append("      </w:tblPr>\n");

        // Table Headers
        sb.append("      <w:tr>\n");
        appendTableCell(sb, "Группа", true, 1200);
        appendTableCell(sb, "Учебная дисциплина", true, 2600);
        appendTableCell(sb, "Дата консультации", true, 1600);
        appendTableCell(sb, "Дата и время экзамена", true, 1600);
        appendTableCell(sb, "Аудитория", true, 1000);
        appendTableCell(sb, "Экзаменатор", true, 1800);
        sb.append("      </w:tr>\n");

        // Table Rows
        for (ExamScheduleItem item : items) {
            sb.append("      <w:tr>\n");
            appendTableCell(sb, item.getGroup(), false, 1200);
            appendTableCell(sb, item.getDiscipline(), false, 2600);
            appendTableCell(sb, item.getConsultationDate(), false, 1600);
            appendTableCell(sb, item.getExamDate() + " в " + item.getExamTime(), false, 1600);
            appendTableCell(sb, item.getClassroom(), false, 1000);
            appendTableCell(sb, item.getExaminer(), false, 1800);
            sb.append("      </w:tr>\n");
        }
        sb.append("    </w:tbl>\n");

        // Document Footer / Signatures
        sb.append("    <w:p>\n");
        sb.append("      <w:pPr><w:spacing w:before=\"360\"/></w:pPr>\n");
        sb.append("      <w:r><w:rPr><w:b/><w:rFonts w:ascii=\"Times New Roman\" w:hAnsi=\"Times New Roman\"/><w:sz w:val=\"24\"/></w:rPr><w:t>Декан факультета / Начальник УМУ: ____________ / А.В. Сорокин /</w:t></w:r>\n");
        sb.append("    </w:p>\n");

        sb.append("  </w:body>\n");
        sb.append("</w:document>");
        return sb.toString();
    }

    private void appendTableCell(StringBuilder sb, String text, boolean isHeader, int width) {
        sb.append("        <w:tc>\n");
        sb.append("          <w:tcPr><w:tcW w:w=\"").append(width).append("\" w:type=\"dxa\"/></w:tcPr>\n");
        sb.append("          <w:p>\n");
        sb.append("            <w:pPr><w:jc w:val=\"").append(isHeader ? "center" : "left").append("\"/></w:pPr>\n");
        sb.append("            <w:r><w:rPr>");
        if (isHeader) {
            sb.append("<w:b/>");
        }
        sb.append("<w:rFonts w:ascii=\"Times New Roman\" w:hAnsi=\"Times New Roman\"/><w:sz w:val=\"20\"/></w:rPr>");
        sb.append("<w:t>").append(escapeXml(text)).append("</w:t></w:r>\n");
        sb.append("          </w:p>\n");
        sb.append("        </w:tc>\n");
    }
}
