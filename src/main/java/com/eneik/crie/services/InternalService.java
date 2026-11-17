package com.eneik.crie.services;

import org.springframework.stereotype.Service;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

@Service
public class InternalService {

    public static final List<String> TARGET_GROUPS = List.of(
        "25ОЭ", "26ОЭ", "25ОИ", "26ОИ", "25ОП", "26ОП", "Аспирантура"
    );
    public static final String SESSION_PERIOD = "25.01 - 25.02";
    public static final String GOST_STANDARD = "ГОСТ Р 7.0.97-2016";
    public static final String DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

    public record ExaminationScheduleRequest(
        List<String> groups,
        String periodStart,
        String periodEnd,
        boolean includePostgraduates,
        String standard
    ) {}

    public record ExaminationScheduleMetadata(
        String documentId,
        String title,
        String period,
        List<String> targetGroups,
        String standard,
        int totalExams,
        long fileSizeBytes,
        String generatedAt
    ) {}

    public boolean isGroupEligible(String group) {
        if (group == null) return false;
        return TARGET_GROUPS.stream().anyMatch(g -> g.equalsIgnoreCase(group.trim()));
    }

    public ExaminationScheduleMetadata generateMetadata(ExaminationScheduleRequest request) {
        List<String> effectiveGroups = (request.groups() == null || request.groups().isEmpty())
            ? TARGET_GROUPS
            : request.groups().stream().filter(this::isGroupEligible).toList();

        return new ExaminationScheduleMetadata(
            UUID.randomUUID().toString(),
            "РАСПИСАНИЕ ЭКЗАМЕНАЦИОННОЙ СЕССИИ (25.01 - 25.02)",
            SESSION_PERIOD,
            effectiveGroups,
            GOST_STANDARD,
            effectiveGroups.size() * 3,
            1024L,
            LocalDate.now().toString()
        );
    }

    public byte[] generateExaminationScheduleDocx(ExaminationScheduleRequest request) throws IOException {
        List<String> groups = (request != null && request.groups() != null && !request.groups().isEmpty())
            ? request.groups()
            : TARGET_GROUPS;

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(baos)) {
            // [Content_Types].xml
            zos.putNextEntry(new ZipEntry("[Content_Types].xml"));
            String contentTypes = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n" +
                "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">\n" +
                "  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>\n" +
                "  <Default Extension=\"xml\" ContentType=\"application/xml\"/>\n" +
                "  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>\n" +
                "</Types>";
            zos.write(contentTypes.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            // _rels/.rels
            zos.putNextEntry(new ZipEntry("_rels/.rels"));
            String rels = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n" +
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n" +
                "  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>\n" +
                "</Relationships>";
            zos.write(rels.getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();

            // word/document.xml formatted according to GOST R 7.0.97-2016
            zos.putNextEntry(new ZipEntry("word/document.xml"));
            StringBuilder doc = new StringBuilder();
            doc.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n")
               .append("<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">\n")
               .append("<w:body>\n")
               .append("  <w:p><w:pPr><w:jc w:val=\"right\"/></w:pPr><w:r><w:t>УТВЕРЖДАЮ</w:t></w:r></w:p>\n")
               .append("  <w:p><w:pPr><w:jc w:val=\"center\"/></w:pPr><w:r><w:rPr><w:b/><w:sz w:val=\"28\"/></w:rPr><w:t>РАСПИСАНИЕ ЭКЗАМЕНАЦИОННОЙ СЕССИИ</w:t></w:r></w:p>\n")
               .append("  <w:p><w:pPr><w:jc w:val=\"center\"/></w:pPr><w:r><w:t>Период: 25.01 - 25.02 (Стандарт: ГОСТ Р 7.0.97-2016)</w:t></w:r></w:p>\n")
               .append("  <w:tbl>\n")
               .append("    <w:tr><w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Академическая группа</w:t></w:r></w:p></w:tc>")
               .append("<w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Дисциплина</w:t></w:r></w:p></w:tc>")
               .append("<w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Дата экзамена</w:t></w:r></w:p></w:tc>")
               .append("<w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Аудитория</w:t></w:r></w:p></w:tc></w:tr>\n");

            int dayOffset = 25;
            for (String group : groups) {
                String dateStr = (dayOffset <= 31 ? dayOffset + ".01" : (dayOffset - 31) + ".02");
                doc.append("    <w:tr>")
                   .append("<w:tc><w:p><w:r><w:t>").append(group).append("</w:t></w:r></w:p></w:tc>")
                   .append("<w:tc><w:p><w:r><w:t>Теоретические основы информатики</w:t></w:r></w:p></w:tc>")
                   .append("<w:tc><w:p><w:r><w:t>").append(dateStr).append(" 09:00</w:t></w:r></w:p></w:tc>")
                   .append("<w:tc><w:p><w:r><w:t>Ауд. 402</w:t></w:r></w:p></w:tc>")
                   .append("</w:tr>\n");
                dayOffset += 2;
            }

            doc.append("  </w:tbl>\n")
               .append("  <w:p><w:r><w:t>Согласовано с учебным отделом по стандарту ГОСТ Р 7.0.97-2016.</w:t></w:r></w:p>\n")
               .append("</w:body>\n")
               .append("</w:document>");

            zos.write(doc.toString().getBytes(StandardCharsets.UTF_8));
            zos.closeEntry();
        }

        return baos.toByteArray();
    }
}
