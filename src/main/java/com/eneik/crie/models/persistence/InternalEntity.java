package com.eneik.crie.models.persistence;

import java.util.Objects;

/**
 * Persistence model and canonical SQLite schema contract for contingent
 * uploaded documents and parsed admission records.
 */
public class InternalEntity {

    public static final String TABLE_UPLOADED_DOCUMENTS = "uploaded_documents";
    public static final String TABLE_ADMISSION_RECORDS = "admission_records";

    public static final String DDL_UPLOADED_DOCUMENTS =
            "CREATE TABLE IF NOT EXISTS uploaded_documents ("
            + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            + "filename TEXT NOT NULL, "
            + "uploaded_at TEXT NOT NULL, "
            + "raw_text TEXT NOT NULL, "
            + "doc_type TEXT NOT NULL, "
            + "content_hash TEXT NOT NULL UNIQUE"
            + ")";

    public static final String DDL_ADMISSION_RECORDS =
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
            + "student_identifiers_json TEXT NOT NULL DEFAULT '[]', "
            + "FOREIGN KEY (doc_id) REFERENCES uploaded_documents(id) ON DELETE CASCADE, "
            + "UNIQUE (order_number, order_date, education_level, specialty_code, financing_type, admission_stage)"
            + ")";

    public static final String QUERY_AGGREGATE_ADMISSIONS =
            "SELECT "
            + "specialty_code, "
            + "specialty_name, "
            + "education_level, "
            + "financing_type, "
            + "admission_stage, "
            + "SUM(enrolled_count) AS total_enrolled, "
            + "COUNT(*) AS record_count, "
            + "GROUP_CONCAT(DISTINCT doc_id) AS doc_ids, "
            + "GROUP_CONCAT(DISTINCT order_number || ' (' || order_date || ')') AS order_references "
            + "FROM admission_records "
            + "GROUP BY specialty_code, specialty_name, education_level, financing_type, admission_stage "
            + "ORDER BY specialty_code ASC, education_level ASC, financing_type ASC, admission_stage ASC";

    private Long id;
    private Long docId;
    private String filename;
    private String uploadedAt;
    private String rawText;
    private String docType;
    private String contentHash;
    private String orderNumber;
    private String orderDate;
    private String educationLevel;
    private String specialtyCode;
    private String specialtyName;
    private String financingType;
    private String admissionStage;
    private int enrolledCount;
    private String studentIdentifiersJson;

    public InternalEntity() {
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getDocId() {
        return docId;
    }

    public void setDocId(Long docId) {
        this.docId = docId;
    }

    public String getFilename() {
        return filename;
    }

    public void setFilename(String filename) {
        this.filename = filename;
    }

    public String getUploadedAt() {
        return uploadedAt;
    }

    public void setUploadedAt(String uploadedAt) {
        this.uploadedAt = uploadedAt;
    }

    public String getRawText() {
        return rawText;
    }

    public void setRawText(String rawText) {
        this.rawText = rawText;
    }

    public String getDocType() {
        return docType;
    }

    public void setDocType(String docType) {
        this.docType = docType;
    }

    public String getContentHash() {
        return contentHash;
    }

    public void setContentHash(String contentHash) {
        this.contentHash = contentHash;
    }

    public String getOrderNumber() {
        return orderNumber;
    }

    public void setOrderNumber(String orderNumber) {
        this.orderNumber = orderNumber;
    }

    public String getOrderDate() {
        return orderDate;
    }

    public void setOrderDate(String orderDate) {
        this.orderDate = orderDate;
    }

    public String getEducationLevel() {
        return educationLevel;
    }

    public void setEducationLevel(String educationLevel) {
        this.educationLevel = educationLevel;
    }

    public String getSpecialtyCode() {
        return specialtyCode;
    }

    public void setSpecialtyCode(String specialtyCode) {
        this.specialtyCode = specialtyCode;
    }

    public String getSpecialtyName() {
        return specialtyName;
    }

    public void setSpecialtyName(String specialtyName) {
        this.specialtyName = specialtyName;
    }

    public String getFinancingType() {
        return financingType;
    }

    public void setFinancingType(String financingType) {
        this.financingType = financingType;
    }

    public String getAdmissionStage() {
        return admissionStage;
    }

    public void setAdmissionStage(String admissionStage) {
        this.admissionStage = admissionStage;
    }

    public int getEnrolledCount() {
        return enrolledCount;
    }

    public void setEnrolledCount(int enrolledCount) {
        this.enrolledCount = enrolledCount;
    }

    public String getStudentIdentifiersJson() {
        return studentIdentifiersJson;
    }

    public void setStudentIdentifiersJson(String studentIdentifiersJson) {
        this.studentIdentifiersJson = studentIdentifiersJson;
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
        return enrolledCount == that.enrolledCount
                && Objects.equals(id, that.id)
                && Objects.equals(docId, that.docId)
                && Objects.equals(filename, that.filename)
                && Objects.equals(uploadedAt, that.uploadedAt)
                && Objects.equals(rawText, that.rawText)
                && Objects.equals(docType, that.docType)
                && Objects.equals(contentHash, that.contentHash)
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
                filename,
                uploadedAt,
                rawText,
                docType,
                contentHash,
                orderNumber,
                orderDate,
                educationLevel,
                specialtyCode,
                specialtyName,
                financingType,
                admissionStage,
                enrolledCount,
                studentIdentifiersJson
        );
    }

    @Override
    public String toString() {
        return "InternalEntity{"
                + "id=" + id
                + ", docId=" + docId
                + ", filename='" + filename + '\''
                + ", orderNumber='" + orderNumber + '\''
                + ", specialtyCode='" + specialtyCode + '\''
                + ", enrolledCount=" + enrolledCount
                + '}';
    }
}
