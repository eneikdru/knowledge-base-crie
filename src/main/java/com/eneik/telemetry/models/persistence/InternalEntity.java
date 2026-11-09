package com.eneik.telemetry.models.persistence;

import java.io.Serializable;
import java.time.Instant;
import java.util.Objects;

/**
 * Persistence entity representing internal official document generation templates
 * and records adhering strictly to GOST R 7.0.97-2016 standards.
 */
public class InternalEntity implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;
    private String documentId;
    private String documentType;
    private String title;
    private String status;
    private String author;

    // GOST R 7.0.97-2016 Typography & Page Layout
    private String fontFamily = "Times New Roman";
    private Integer fontSizePt = 14;
    private Double lineSpacing = 1.5;
    private Double marginLeftMm = 30.0;
    private Double marginRightMm = 10.0;
    private Double marginTopMm = 20.0;
    private Double marginBottomMm = 20.0;

    // Academic & Curricular Invariants
    private Integer totalCredits = 120;
    private Integer totalHours = 4320;
    private Double facultyDegreeRatio = 0.70;

    // Verification & Stamps
    private Boolean officialStampRequired = true;
    private Boolean quorumVerified = false;
    private Boolean gostCompliant = true;

    // Payload & Audit Trail
    private String payloadJson;
    private Instant createdAt;
    private Instant updatedAt;

    public InternalEntity() {
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    public InternalEntity(String documentId, String documentType, String title, String status) {
        this();
        this.documentId = documentId;
        this.documentType = documentType;
        this.title = title;
        this.status = status;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getDocumentId() {
        return documentId;
    }

    public void setDocumentId(String documentId) {
        this.documentId = documentId;
    }

    public String getDocumentType() {
        return documentType;
    }

    public void setDocumentType(String documentType) {
        this.documentType = documentType;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getAuthor() {
        return author;
    }

    public void setAuthor(String author) {
        this.author = author;
    }

    public String getFontFamily() {
        return fontFamily;
    }

    public void setFontFamily(String fontFamily) {
        this.fontFamily = fontFamily;
    }

    public Integer getFontSizePt() {
        return fontSizePt;
    }

    public void setFontSizePt(Integer fontSizePt) {
        this.fontSizePt = fontSizePt;
    }

    public Double getLineSpacing() {
        return lineSpacing;
    }

    public void setLineSpacing(Double lineSpacing) {
        this.lineSpacing = lineSpacing;
    }

    public Double getMarginLeftMm() {
        return marginLeftMm;
    }

    public void setMarginLeftMm(Double marginLeftMm) {
        this.marginLeftMm = marginLeftMm;
    }

    public Double getMarginRightMm() {
        return marginRightMm;
    }

    public void setMarginRightMm(Double marginRightMm) {
        this.marginRightMm = marginRightMm;
    }

    public Double getMarginTopMm() {
        return marginTopMm;
    }

    public void setMarginTopMm(Double marginTopMm) {
        this.marginTopMm = marginTopMm;
    }

    public Double getMarginBottomMm() {
        return marginBottomMm;
    }

    public void setMarginBottomMm(Double marginBottomMm) {
        this.marginBottomMm = marginBottomMm;
    }

    public Integer getTotalCredits() {
        return totalCredits;
    }

    public void setTotalCredits(Integer totalCredits) {
        this.totalCredits = totalCredits;
    }

    public Integer getTotalHours() {
        return totalHours;
    }

    public void setTotalHours(Integer totalHours) {
        this.totalHours = totalHours;
    }

    public Double getFacultyDegreeRatio() {
        return facultyDegreeRatio;
    }

    public void setFacultyDegreeRatio(Double facultyDegreeRatio) {
        this.facultyDegreeRatio = facultyDegreeRatio;
    }

    public Boolean getOfficialStampRequired() {
        return officialStampRequired;
    }

    public void setOfficialStampRequired(Boolean officialStampRequired) {
        this.officialStampRequired = officialStampRequired;
    }

    public Boolean getQuorumVerified() {
        return quorumVerified;
    }

    public void setQuorumVerified(Boolean quorumVerified) {
        this.quorumVerified = quorumVerified;
    }

    public Boolean getGostCompliant() {
        return gostCompliant;
    }

    public void setGostCompliant(Boolean gostCompliant) {
        this.gostCompliant = gostCompliant;
    }

    public String getPayloadJson() {
        return payloadJson;
    }

    public void setPayloadJson(String payloadJson) {
        this.payloadJson = payloadJson;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        InternalEntity that = (InternalEntity) o;
        return Objects.equals(id, that.id) && Objects.equals(documentId, that.documentId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, documentId);
    }

    @Override
    public String toString() {
        return "InternalEntity{" +
                "id=" + id +
                ", documentId='" + documentId + '\'' +
                ", documentType='" + documentType + '\'' +
                ", title='" + title + '\'' +
                ", status='" + status + '\'' +
                ", totalCredits=" + totalCredits +
                ", totalHours=" + totalHours +
                ", facultyDegreeRatio=" + facultyDegreeRatio +
                ", gostCompliant=" + gostCompliant +
                '}';
    }
}
