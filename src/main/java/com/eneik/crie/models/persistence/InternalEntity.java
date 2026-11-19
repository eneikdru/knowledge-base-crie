package com.eneik.crie.models.persistence;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * Persistence schema model for uploaded admission documents and parsed enrollment records.
 */
public class InternalEntity {

    public static final String TABLE_UPLOADED_DOCUMENTS = "uploaded_documents";
    public static final String TABLE_ADMISSION_RECORDS = "admission_records";

    public static final Set<String> EDUCATION_LEVELS = Collections.unmodifiableSet(
            new LinkedHashSet<String>(Arrays.asList("ординатура", "аспирантура")));

    public static final Set<String> FINANCING_TYPES = Collections.unmodifiableSet(
            new LinkedHashSet<String>(Arrays.asList("бюджет", "целевая квота", "договор")));

    public static final Set<String> ADMISSION_STAGES = Collections.unmodifiableSet(
            new LinkedHashSet<String>(Arrays.asList("основной", "допконкурс")));

    private final UploadedDocument document;
    private final List<AdmissionRecord> admissionRecords;

    /**
     * Creates an aggregate persistence entity pairing a source document with its parsed records.
     */
    public InternalEntity(UploadedDocument document, List<AdmissionRecord> admissionRecords) {
        this.document = Objects.requireNonNull(document, "document must not be null");
        if (admissionRecords == null) {
            this.admissionRecords = Collections.emptyList();
        } else {
            this.admissionRecords = Collections.unmodifiableList(new ArrayList<AdmissionRecord>(admissionRecords));
        }
    }

    public UploadedDocument getDocument() {
        return document;
    }

    public List<AdmissionRecord> getAdmissionRecords() {
        return admissionRecords;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof InternalEntity)) {
            return false;
        }
        InternalEntity that = (InternalEntity) o;
        return Objects.equals(document, that.document)
                && Objects.equals(admissionRecords, that.admissionRecords);
    }

    @Override
    public int hashCode() {
        return Objects.hash(document, admissionRecords);
    }

    /**
     * Represents a row in the {@code uploaded_documents} SQLite table.
     */
    public static final class UploadedDocument {
        private final Long id;
        private final String filename;
        private final Instant uploadedAt;
        private final String rawText;
        private final String docType;
        private final String contentHash;

        public UploadedDocument(
                Long id,
                String filename,
                Instant uploadedAt,
                String rawText,
                String docType,
                String contentHash) {
            this.id = id;
            this.filename = requireNonBlank(filename, "filename");
            this.uploadedAt = Objects.requireNonNull(uploadedAt, "uploadedAt must not be null");
            this.rawText = Objects.requireNonNull(rawText, "rawText must not be null");
            this.docType = requireNonBlank(docType, "docType");
            this.contentHash = requireNonBlank(contentHash, "contentHash");
        }

        public Long getId() {
            return id;
        }

        public String getFilename() {
            return filename;
        }

        public Instant getUploadedAt() {
            return uploadedAt;
        }

        public String getRawText() {
            return rawText;
        }

        public String getDocType() {
            return docType;
        }

        public String getContentHash() {
            return contentHash;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) {
                return true;
            }
            if (!(o instanceof UploadedDocument)) {
                return false;
            }
            UploadedDocument that = (UploadedDocument) o;
            return Objects.equals(id, that.id)
                    && Objects.equals(filename, that.filename)
                    && Objects.equals(uploadedAt, that.uploadedAt)
                    && Objects.equals(rawText, that.rawText)
                    && Objects.equals(docType, that.docType)
                    && Objects.equals(contentHash, that.contentHash);
        }

        @Override
        public int hashCode() {
            return Objects.hash(id, filename, uploadedAt, rawText, docType, contentHash);
        }
    }

    /**
     * Represents a row in the {@code admission_records} SQLite table.
     */
    public static final class AdmissionRecord {
        private final Long id;
        private final Long docId;
        private final String orderNumber;
        private final String orderDate;
        private final String educationLevel;
        private final String specialtyCode;
        private final String specialtyName;
        private final String financingType;
        private final String admissionStage;
        private final int enrolledCount;
        private final String studentIdentifiersJson;

        public AdmissionRecord(
                Long id,
                Long docId,
                String orderNumber,
                String orderDate,
                String educationLevel,
                String specialtyCode,
                String specialtyName,
                String financingType,
                String admissionStage,
                int enrolledCount,
                String studentIdentifiersJson) {
            this.id = id;
            this.docId = docId;
            this.orderNumber = requireNonBlank(orderNumber, "orderNumber");
            this.orderDate = requireNonBlank(orderDate, "orderDate");
            this.educationLevel = validateAllowed(educationLevel, EDUCATION_LEVELS, "educationLevel");
            this.specialtyCode = requireNonBlank(specialtyCode, "specialtyCode");
            this.specialtyName = requireNonBlank(specialtyName, "specialtyName");
            this.financingType = validateAllowed(financingType, FINANCING_TYPES, "financingType");
            this.admissionStage = validateAllowed(admissionStage, ADMISSION_STAGES, "admissionStage");
            if (enrolledCount < 0) {
                throw new IllegalArgumentException("enrolledCount must be non-negative");
            }
            this.enrolledCount = enrolledCount;
            this.studentIdentifiersJson = requireNonBlank(studentIdentifiersJson, "studentIdentifiersJson");
        }

        public Long getId() {
            return id;
        }

        public Long getDocId() {
            return docId;
        }

        public String getOrderNumber() {
            return orderNumber;
        }

        public String getOrderDate() {
            return orderDate;
        }

        public String getEducationLevel() {
            return educationLevel;
        }

        public String getSpecialtyCode() {
            return specialtyCode;
        }

        public String getSpecialtyName() {
            return specialtyName;
        }

        public String getFinancingType() {
            return financingType;
        }

        public String getAdmissionStage() {
            return admissionStage;
        }

        public int getEnrolledCount() {
            return enrolledCount;
        }

        public String getStudentIdentifiersJson() {
            return studentIdentifiersJson;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) {
                return true;
            }
            if (!(o instanceof AdmissionRecord)) {
                return false;
            }
            AdmissionRecord that = (AdmissionRecord) o;
            return enrolledCount == that.enrolledCount
                    && Objects.equals(id, that.id)
                    && Objects.equals(docId, that.docId)
                    && Objects.equals(orderNumber, that.orderNumber)
                    && Objects.equals(orderDate, that.orderDate)
                    && Objects.equals(educationLevel, that.educationLevel)
                    && Objects.equals(specialtyCode, that.specialtyCode)
                    && Objects.equals(specialtyName, that.specialtyName)
                    && Objects.equals(financingType, that.financingType)
                    && Objects.equals(admissionStage, that.admissionStage)
                    && Objects.equals(studentIdentifiersJson, that.studentIdentifiersJson);
        }

        @Override
        public int hashCode() {
            return Objects.hash(
                    id,
                    docId,
                    orderNumber,
                    orderDate,
                    educationLevel,
                    specialtyCode,
                    specialtyName,
                    financingType,
                    admissionStage,
                    enrolledCount,
                    studentIdentifiersJson);
        }
    }

    private static String requireNonBlank(String value, String fieldName) {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException(fieldName + " must not be blank");
        }
        return value;
    }

    private static String validateAllowed(String value, Set<String> allowed, String fieldName) {
        String checked = requireNonBlank(value, fieldName);
        if (!allowed.contains(checked)) {
            throw new IllegalArgumentException(
                    "Unsupported " + fieldName + ": " + checked + "; expected one of " + allowed);
        }
        return checked;
    }
}
