package com.eneik.crie.models.persistence;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.LocalDate;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

/**
 * Persistence schema constants, domain enumerations, and immutable value records
 * for uploaded admission PDFs and structured enrollment records.
 */
public class InternalEntity {

    public static final String TABLE_UPLOADED_DOCUMENTS = "uploaded_documents";
    public static final String TABLE_ADMISSION_RECORDS = "admission_records";

    public static final String SQL_CREATE_UPLOADED_DOCUMENTS =
            "CREATE TABLE IF NOT EXISTS uploaded_documents ("
                    + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + "filename TEXT NOT NULL, "
                    + "uploaded_at TEXT NOT NULL, "
                    + "raw_text TEXT NOT NULL, "
                    + "doc_type TEXT NOT NULL, "
                    + "content_sha256 TEXT NOT NULL UNIQUE"
                    + ")";

    public static final String SQL_CREATE_ADMISSION_RECORDS =
            "CREATE TABLE IF NOT EXISTS admission_records ("
                    + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + "doc_id INTEGER NOT NULL, "
                    + "order_number TEXT NOT NULL, "
                    + "order_date TEXT NOT NULL, "
                    + "education_level TEXT NOT NULL CHECK (education_level IN ('ординатура', 'аспирантура')), "
                    + "specialty_code TEXT NOT NULL, "
                    + "specialty_name TEXT NOT NULL, "
                    + "financing_type TEXT NOT NULL CHECK (financing_type IN ('бюджет', 'целевая квота', 'договор')), "
                    + "admission_stage TEXT NOT NULL CHECK (admission_stage IN ('основной', 'допконкурс')), "
                    + "enrolled_count INTEGER NOT NULL CHECK (enrolled_count >= 0), "
                    + "student_identifiers_json TEXT NOT NULL, "
                    + "FOREIGN KEY (doc_id) REFERENCES uploaded_documents(id) ON DELETE CASCADE"
                    + ")";

    private InternalEntity() {
    }

    /**
     * Supported admission document categories.
     */
    public enum DocumentType {
        ZACHISLENIE("zachislenie"),
        PRIEM("priem");

        private final String wireValue;

        DocumentType(String wireValue) {
            this.wireValue = wireValue;
        }

        public String getWireValue() {
            return wireValue;
        }
    }

    /**
     * Postgraduate education levels tracked in admission_records.
     */
    public enum EducationLevel {
        ORDINATURA("ординатура"),
        ASPIRANTURA("аспирантура");

        private final String label;

        EducationLevel(String label) {
            this.label = label;
        }

        public String getLabel() {
            return label;
        }
    }

    /**
     * Funding categories tracked in admission_records.
     */
    public enum FinancingType {
        BUDGET("бюджет"),
        TARGET_QUOTA("целевая квота"),
        CONTRACT("договор");

        private final String label;

        FinancingType(String label) {
            this.label = label;
        }

        public String getLabel() {
            return label;
        }
    }

    /**
     * Admission wave stages tracked in admission_records.
     */
    public enum AdmissionStage {
        MAIN("основной"),
        ADDITIONAL("допконкурс");

        private final String label;

        AdmissionStage(String label) {
            this.label = label;
        }

        public String getLabel() {
            return label;
        }
    }

    /**
     * Computes a deterministic SHA-256 hex digest over whitespace-normalized text
     * for duplicate document detection.
     *
     * @param rawText extracted PDF text
     * @return lowercase 64-character hex digest
     */
    public static String computeNormalizedContentHash(String rawText) {
        Objects.requireNonNull(rawText, "rawText must not be null");
        String normalized = rawText.trim().replaceAll("\\s+", " ").toLowerCase(Locale.ROOT);
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(normalized.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 algorithm is unavailable", ex);
        }
    }

    /**
     * Immutable representation of a row in uploaded_documents.
     */
    public static final class UploadedDocumentRecord {
        private final Long id;
        private final String filename;
        private final Instant uploadedAt;
        private final String rawText;
        private final DocumentType docType;
        private final String contentSha256;

        public UploadedDocumentRecord(
                Long id,
                String filename,
                Instant uploadedAt,
                String rawText,
                DocumentType docType,
                String contentSha256) {
            this.id = id;
            this.filename = requireNonBlank(filename, "filename");
            this.uploadedAt = Objects.requireNonNull(uploadedAt, "uploadedAt must not be null");
            this.rawText = Objects.requireNonNull(rawText, "rawText must not be null");
            this.docType = Objects.requireNonNull(docType, "docType must not be null");
            this.contentSha256 = (contentSha256 == null || contentSha256.isBlank())
                    ? computeNormalizedContentHash(rawText)
                    : contentSha256;
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

        public DocumentType getDocType() {
            return docType;
        }

        public String getContentSha256() {
            return contentSha256;
        }
    }

    /**
     * Immutable representation of a row in admission_records.
     */
    public static final class AdmissionRecord {
        private final Long id;
        private final Long docId;
        private final String orderNumber;
        private final LocalDate orderDate;
        private final EducationLevel educationLevel;
        private final String specialtyCode;
        private final String specialtyName;
        private final FinancingType financingType;
        private final AdmissionStage admissionStage;
        private final int enrolledCount;
        private final List<String> studentIdentifiers;

        public AdmissionRecord(
                Long id,
                Long docId,
                String orderNumber,
                LocalDate orderDate,
                EducationLevel educationLevel,
                String specialtyCode,
                String specialtyName,
                FinancingType financingType,
                AdmissionStage admissionStage,
                int enrolledCount,
                List<String> studentIdentifiers) {
            if (enrolledCount < 0) {
                throw new IllegalArgumentException("enrolledCount must be non-negative");
            }
            this.id = id;
            this.docId = docId;
            this.orderNumber = requireNonBlank(orderNumber, "orderNumber");
            this.orderDate = Objects.requireNonNull(orderDate, "orderDate must not be null");
            this.educationLevel = Objects.requireNonNull(educationLevel, "educationLevel must not be null");
            this.specialtyCode = requireNonBlank(specialtyCode, "specialtyCode");
            this.specialtyName = requireNonBlank(specialtyName, "specialtyName");
            this.financingType = Objects.requireNonNull(financingType, "financingType must not be null");
            this.admissionStage = Objects.requireNonNull(admissionStage, "admissionStage must not be null");
            this.enrolledCount = enrolledCount;
            this.studentIdentifiers = studentIdentifiers == null
                    ? Collections.emptyList()
                    : List.copyOf(studentIdentifiers);
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

        public LocalDate getOrderDate() {
            return orderDate;
        }

        public EducationLevel getEducationLevel() {
            return educationLevel;
        }

        public String getSpecialtyCode() {
            return specialtyCode;
        }

        public String getSpecialtyName() {
            return specialtyName;
        }

        public FinancingType getFinancingType() {
            return financingType;
        }

        public AdmissionStage getAdmissionStage() {
            return admissionStage;
        }

        public int getEnrolledCount() {
            return enrolledCount;
        }

        public List<String> getStudentIdentifiers() {
            return studentIdentifiers;
        }
    }

    /**
     * Structured diagnostic emitted when a PDF fails validation or parsing.
     */
    public static final class IngestionDiagnostic {
        private final String filename;
        private final String errorCode;
        private final String message;

        public IngestionDiagnostic(String filename, String errorCode, String message) {
            this.filename = requireNonBlank(filename, "filename");
            this.errorCode = requireNonBlank(errorCode, "errorCode");
            this.message = requireNonBlank(message, "message");
        }

        public String getFilename() {
            return filename;
        }

        public String getErrorCode() {
            return errorCode;
        }

        public String getMessage() {
            return message;
        }
    }

    private static String requireNonBlank(String value, String fieldName) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(fieldName + " must not be blank");
        }
        return value;
    }
}
