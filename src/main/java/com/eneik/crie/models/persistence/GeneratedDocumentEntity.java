package com.eneik.crie.models.persistence;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

/**
 * Persistence entity representing generated institutional document artifacts,
 * SHA-256 provenance hashes, generation parameters, and bidirectional entity relationships.
 */
public class GeneratedDocumentEntity {

    private UUID id;
    private String documentType;
    private String title;
    private String contentArtifact;
    private String sha256Checksum;
    private String author;
    private String targetEntityId;
    private String entityType;
    private String sourceKbRefs;
    private String generationParameters;
    private Instant createdAt;
    private Instant updatedAt;

    public GeneratedDocumentEntity() {
        this.id = UUID.randomUUID();
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    public GeneratedDocumentEntity(UUID id,
                                   String documentType,
                                   String title,
                                   String contentArtifact,
                                   String sha256Checksum,
                                   String author,
                                   String targetEntityId,
                                   String entityType,
                                   String sourceKbRefs,
                                   String generationParameters,
                                   Instant createdAt,
                                   Instant updatedAt) {
        this.id = id != null ? id : UUID.randomUUID();
        this.documentType = documentType;
        this.title = title;
        this.contentArtifact = contentArtifact;
        this.sha256Checksum = sha256Checksum;
        this.author = author;
        this.targetEntityId = targetEntityId;
        this.entityType = entityType;
        this.sourceKbRefs = sourceKbRefs;
        this.generationParameters = generationParameters;
        this.createdAt = createdAt != null ? createdAt : Instant.now();
        this.updatedAt = updatedAt != null ? updatedAt : Instant.now();
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

    public String getContentArtifact() {
        return contentArtifact;
    }

    public void setContentArtifact(String contentArtifact) {
        this.contentArtifact = contentArtifact;
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

    public String getTargetEntityId() {
        return targetEntityId;
    }

    public void setTargetEntityId(String targetEntityId) {
        this.targetEntityId = targetEntityId;
    }

    public String getEntityType() {
        return entityType;
    }

    public void setEntityType(String entityType) {
        this.entityType = entityType;
    }

    public String getSourceKbRefs() {
        return sourceKbRefs;
    }

    public void setSourceKbRefs(String sourceKbRefs) {
        this.sourceKbRefs = sourceKbRefs;
    }

    public String getGenerationParameters() {
        return generationParameters;
    }

    public void setGenerationParameters(String generationParameters) {
        this.generationParameters = generationParameters;
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
        GeneratedDocumentEntity that = (GeneratedDocumentEntity) o;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "GeneratedDocumentEntity{" +
                "id=" + id +
                ", documentType='" + documentType + '\'' +
                ", title='" + title + '\'' +
                ", sha256Checksum='" + sha256Checksum + '\'' +
                ", author='" + author + '\'' +
                ", targetEntityId='" + targetEntityId + '\'' +
                ", entityType='" + entityType + '\'' +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                '}';
    }
}
