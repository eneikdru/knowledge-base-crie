package com.eneik.crie.models.persistence;

import java.time.Instant;
import java.util.Objects;

/**
 * Persistence model representing contingent admission document and record state
 * aligned with the SQLite {@code uploaded_documents} and {@code admission_records} tables.
 */
public class InternalEntity {

    public static final String TABLE_UPLOADED_DOCUMENTS = "uploaded_documents";
    public static final String TABLE_ADMISSION_RECORDS = "admission_records";

    private Long id;
    private Long docId;
    private String filename;
    private Instant uploadedAt;
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

    public InternalEntity(
            Long id,
            Long docId,
            String filename,
            Instant uploadedAt,
            String docType,
            String contentHash,
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
        this.filename = filename;
        this.uploadedAt = uploadedAt;
        this.docType = docType;
        this.contentHash = contentHash;
        this.orderNumber = orderNumber;
        this.orderDate = orderDate;
        this.educationLevel = educationLevel;
        this.specialtyCode = specialtyCode;
        this.specialtyName = specialtyName;
        this.financingType = financingType;
        this.admissionStage = admissionStage;
        this.enrolledCount = enrolledCount;
        this.studentIdentifiersJson = studentIdentifiersJson;
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

    public Instant getUploadedAt() {
        return uploadedAt;
    }

    public void setUploadedAt(Instant uploadedAt) {
        this.uploadedAt = uploadedAt;
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
                studentIdentifiersJson);
    }

    @Override
    public String toString() {
        return "InternalEntity{"
                + "id=" + id
                + ", docId=" + docId
                + ", filename='" + filename + '\''
                + ", docType='" + docType + '\''
                + ", orderNumber='" + orderNumber + '\''
                + ", orderDate='" + orderDate + '\''
                + ", educationLevel='" + educationLevel + '\''
                + ", specialtyCode='" + specialtyCode + '\''
                + ", financingType='" + financingType + '\''
                + ", admissionStage='" + admissionStage + '\''
                + ", enrolledCount=" + enrolledCount
                + '}';
    }
}
