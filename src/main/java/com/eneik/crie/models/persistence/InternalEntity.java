package com.eneik.crie.models.persistence;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * Persistent entity capturing generated institutional document artifacts,
 * SHA-256 provenance hashes, generation parameters, and bidirectional entity linkages.
 */
public class InternalEntity {

    private UUID id;
    private String documentType;
    private String title;
    private String contentPayload;
    private String sha256Checksum;
    private String author;
    private Instant createdAt;
    private String generationParameters;
    private List<String> sourceKnowledgeBaseReferences;
    private String targetEntityId;
    private String departmentId;
    private String status;

    public InternalEntity() {
        this.id = UUID.randomUUID();
        this.createdAt = Instant.now();
        this.sourceKnowledgeBaseReferences = new ArrayList<>();
        this.status = "DRAFT";
    }

    public InternalEntity(
            UUID id,
            String documentType,
            String title,
            String contentPayload,
            String sha256Checksum,
            String author,
            Instant createdAt,
            String generationParameters,
            List<String> sourceKnowledgeBaseReferences,
            String targetEntityId,
            String departmentId,
            String status
    ) {
        this.id = id != null ? id : UUID.randomUUID();
        this.documentType = documentType;
        this.title = title;
        this.contentPayload = contentPayload;
        this.sha256Checksum = sha256Checksum;
        this.author = author;
        this.createdAt = createdAt != null ? createdAt : Instant.now();
        this.generationParameters = generationParameters;
        this.sourceKnowledgeBaseReferences = sourceKnowledgeBaseReferences != null ? new ArrayList<>(sourceKnowledgeBaseReferences) : new ArrayList<>();
        this.targetEntityId = targetEntityId;
        this.departmentId = departmentId;
        this.status = status != null ? status : "DRAFT";
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
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

    public String getContentPayload() {
        return contentPayload;
    }

    public void setContentPayload(String contentPayload) {
        this.contentPayload = contentPayload;
    }

    public String getSha256Checksum() {
        return sha256Checksum;
    }

    public void setSha256Checksum(String sha256Checksum) {
        this.sha256Checksum = sha256Checksum;
    }

    public String getAuthor() {
        return author;
    }

    public void setAuthor(String author) {
        this.author = author;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public String getGenerationParameters() {
        return generationParameters;
    }

    public void setGenerationParameters(String generationParameters) {
        this.generationParameters = generationParameters;
    }

    public List<String> getSourceKnowledgeBaseReferences() {
        return sourceKnowledgeBaseReferences;
    }

    public void setSourceKnowledgeBaseReferences(List<String> sourceKnowledgeBaseReferences) {
        this.sourceKnowledgeBaseReferences = sourceKnowledgeBaseReferences != null ? new ArrayList<>(sourceKnowledgeBaseReferences) : new ArrayList<>();
    }

    public String getTargetEntityId() {
        return targetEntityId;
    }

    public void setTargetEntityId(String targetEntityId) {
        this.targetEntityId = targetEntityId;
    }

    public String getDepartmentId() {
        return departmentId;
    }

    public void setDepartmentId(String departmentId) {
        this.departmentId = departmentId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        InternalEntity that = (InternalEntity) o;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "InternalEntity{" +
                "id=" + id +
                ", documentType='" + documentType + '\'' +
                ", title='" + title + '\'' +
                ", sha256Checksum='" + sha256Checksum + '\'' +
                ", author='" + author + '\'' +
                ", createdAt=" + createdAt +
                ", targetEntityId='" + targetEntityId + '\'' +
                ", departmentId='" + departmentId + '\'' +
                ", status='" + status + '\'' +
                '}';
    }
}
