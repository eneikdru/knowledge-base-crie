package com.eneik.crie.models.persistence;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.time.Instant;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.function.Supplier;

/**
 * Persistence schema contract and domain models for the CRIE admission PDF registry
 * ({@code uploaded_documents}, {@code admission_records}, and {@code ingestion_diagnostics}).
 */
public class InternalEntity {

    public static final String TABLE_UPLOADED_DOCUMENTS = "uploaded_documents";
    public static final String TABLE_ADMISSION_RECORDS = "admission_records";
    public static final String TABLE_INGESTION_DIAGNOSTICS = "ingestion_diagnostics";

    public static final String DDL_UPLOADED_DOCUMENTS =
            "CREATE TABLE IF NOT EXISTS uploaded_documents ("
                    + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + "filename TEXT NOT NULL, "
                    + "uploaded_at TEXT NOT NULL, "
                    + "raw_text TEXT NOT NULL, "
                    + "doc_type TEXT NOT NULL, "
                    + "content_hash TEXT NOT NULL UNIQUE, "
                    + "status TEXT NOT NULL DEFAULT 'INGESTED'"
                    + ")";

    public static final String DDL_ADMISSION_RECORDS =
            "CREATE TABLE IF NOT EXISTS admission_records ("
                    + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + "doc_id INTEGER NOT NULL REFERENCES uploaded_documents(id) ON DELETE CASCADE, "
                    + "order_number TEXT NOT NULL, "
                    + "order_date TEXT NOT NULL, "
                    + "education_level TEXT NOT NULL CHECK (education_level IN ('ординатура', 'аспирантура')), "
                    + "specialty_code TEXT NOT NULL, "
                    + "specialty_name TEXT NOT NULL, "
                    + "financing_type TEXT NOT NULL CHECK (financing_type IN ('бюджет', 'целевая квота', 'договор')), "
                    + "admission_stage TEXT NOT NULL CHECK (admission_stage IN ('основной', 'допконкурс')), "
                    + "enrolled_count INTEGER NOT NULL CHECK (enrolled_count >= 0), "
                    + "student_identifiers_json TEXT NOT NULL, "
                    + "UNIQUE (doc_id, order_number, specialty_code, financing_type, admission_stage)"
                    + ")";

    public static final String DDL_INGESTION_DIAGNOSTICS =
            "CREATE TABLE IF NOT EXISTS ingestion_diagnostics ("
                    + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + "filename TEXT NOT NULL, "
                    + "content_hash TEXT NOT NULL, "
                    + "error_code TEXT NOT NULL, "
                    + "error_message TEXT NOT NULL, "
                    + "recorded_at TEXT NOT NULL, "
                    + "status TEXT NOT NULL DEFAULT 'FAILED' CHECK (status IN ('FAILED', 'ACKNOWLEDGED', 'RESOLVED'))"
                    + ")";

    /**
     * Atomically guarded status update preventing concurrent resurrection of terminal states.
     */
    public static final String SQL_GUARDED_STATUS_UPDATE =
            "UPDATE ingestion_diagnostics SET status = ? WHERE id = ? AND status = ?";

    private final Clock clock;
    private final Supplier<String> idGenerator;

    public InternalEntity() {
        this(Clock.systemUTC(), () -> Long.toString(System.nanoTime()));
    }

    public InternalEntity(Clock clock, Supplier<String> idGenerator) {
        this.clock = Objects.requireNonNull(clock, "clock must not be null");
        this.idGenerator = Objects.requireNonNull(idGenerator, "idGenerator must not be null");
    }

    public Instant currentTimestamp() {
        return clock.instant();
    }

    public String nextCorrelationId() {
        return idGenerator.get();
    }

    /**
     * Computes a deterministic SHA-256 hex digest over normalized document text for deduplication.
     */
    public static String computeNormalizedHash(String rawText) {
        Objects.requireNonNull(rawText, "rawText must not be null");
        String normalized = rawText.trim().replaceAll("\\s+", " ");
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(normalized.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 unavailable", ex);
        }
    }

    public enum DocumentType {
        ZACHISLENIE("zachislenie"),
        PRIEM("priem");

        private final String dbValue;

        DocumentType(String dbValue) {
            this.dbValue = dbValue;
        }

        public String getDbValue() {
            return dbValue;
        }
    }

    public enum EducationLevel {
        ORDINATURA("ординатура"),
        ASPIRANTURA("аспирантура");

        private final String dbValue;

        EducationLevel(String dbValue) {
            this.dbValue = dbValue;
        }

        public String getDbValue() {
            return dbValue;
        }
    }

    public enum FinancingType {
        BUDGET("бюджет"),
        TARGET_QUOTA("целевая квота"),
        CONTRACT("договор");

        private final String dbValue;

        FinancingType(String dbValue) {
            this.dbValue = dbValue;
        }

        public String getDbValue() {
            return dbValue;
        }
    }

    public enum AdmissionStage {
        MAIN("основной"),
        ADDITIONAL("допконкурс");

        private final String dbValue;

        AdmissionStage(String dbValue) {
            this.dbValue = dbValue;
        }

        public String getDbValue() {
            return dbValue;
        }
    }

    public enum IngestionStatus {
        INGESTED,
        FAILED,
        ACKNOWLEDGED,
        RESOLVED;

        public boolean isTerminal() {
            return this == RESOLVED;
        }
    }

    public static final class UploadedDocument {
        private final Long id;
        private final String filename;
        private final String uploadedAt;
        private final String rawText;
        private final DocumentType docType;
        private final String contentHash;
        private final IngestionStatus status;

        public UploadedDocument(
                Long id,
                String filename,
                String uploadedAt,
                String rawText,
                DocumentType docType,
                String contentHash,
                IngestionStatus status) {
            this.id = id;
            this.filename = requireNonBlank(filename, "filename");
            this.uploadedAt = requireNonBlank(uploadedAt, "uploadedAt");
            this.rawText = Objects.requireNonNull(rawText, "rawText must not be null");
            this.docType = Objects.requireNonNull(docType, "docType must not be null");
            this.contentHash = requireNonBlank(contentHash, "contentHash");
            this.status = Objects.requireNonNull(status, "status must not be null");
        }

        public Long getId() {
            return id;
        }

        public String getFilename() {
            return filename;
        }

        public String getUploadedAt() {
            return uploadedAt;
        }

        public String getRawText() {
            return rawText;
        }

        public DocumentType getDocType() {
            return docType;
        }

        public String getContentHash() {
            return contentHash;
        }

        public IngestionStatus getStatus() {
            return status;
        }
    }

    public static final class AdmissionRecord {
        private final Long id;
        private final long docId;
        private final String orderNumber;
        private final String orderDate;
        private final EducationLevel educationLevel;
        private final String specialtyCode;
        private final String specialtyName;
        private final FinancingType financingType;
        private final AdmissionStage admissionStage;
        private final int enrolledCount;
        private final List<String> studentIdentifiers;

        public AdmissionRecord(
                Long id,
                long docId,
                String orderNumber,
                String orderDate,
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
            this.orderDate = requireNonBlank(orderDate, "orderDate");
            this.educationLevel = Objects.requireNonNull(educationLevel, "educationLevel must not be null");
            this.specialtyCode = requireNonBlank(specialtyCode, "specialtyCode");
            this.specialtyName = requireNonBlank(specialtyName, "specialtyName");
            this.financingType = Objects.requireNonNull(financingType, "financingType must not be null");
            this.admissionStage = Objects.requireNonNull(admissionStage, "admissionStage must not be null");
            this.enrolledCount = enrolledCount;
            this.studentIdentifiers = Collections.unmodifiableList(
                    Objects.requireNonNull(studentIdentifiers, "studentIdentifiers must not be null"));
        }

        public Long getId() {
            return id;
        }

        public long getDocId() {
            return docId;
        }

        public String getOrderNumber() {
            return orderNumber;
        }

        public String getOrderDate() {
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

    private static String requireNonBlank(String value, String fieldName) {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException(fieldName + " must not be blank");
        }
        return value;
    }
}
