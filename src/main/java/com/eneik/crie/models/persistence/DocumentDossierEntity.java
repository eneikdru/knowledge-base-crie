package com.eneik.crie.models.persistence;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

/**
 * Persistence entity representing an official academic administrative document dossier entry
 * linked to an entity card (resident, PhD student, supervisor, commission, department).
 */
public class DocumentDossierEntity {

    private UUID id;
    private String targetEntityId;
    private String targetEntityType;
    private String documentType;
    private String storageKey;
    private String documentTitle;
    private String mimeType;
    private long fileSizeBytes;
    private String sha256Checksum;
    private String generationAgentVersion;
    private boolean validated;
    private Instant createdAt;
    private Instant updatedAt;

    public DocumentDossierEntity() {
        this.id = UUID.randomUUID();
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
        this.validated = false;
    }

    public DocumentDossierEntity(UUID id,
                                 String targetEntityId,
                                 String targetEntityType,
                                 String documentType,
                                 String storageKey,
                                 String documentTitle,
                                 String mimeType,
                                 long fileSizeBytes,
                                 String sha256Checksum,
                                 String generationAgentVersion,
                                 boolean validated,
                                 Instant createdAt,
                                 Instant updatedAt) {
        this.id = id != null ? id : UUID.randomUUID();
        this.targetEntityId = targetEntityId;
        this.targetEntityType = targetEntityType;
        this.documentType = documentType;
        this.storageKey = storageKey;
        this.documentTitle = documentTitle;
        this.mimeType = mimeType;
        this.fileSizeBytes = fileSizeBytes;
        this.sha256Checksum = sha256Checksum;
        this.generationAgentVersion = generationAgentVersion;
        this.validated = validated;
        this.createdAt = createdAt != null ? createdAt : Instant.now();
        this.updatedAt = updatedAt != null ? updatedAt : Instant.now();
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public String getTargetEntityId() {
        return targetEntityId;
    }

    public void setTargetEntityId(String targetEntityId) {
        this.targetEntityId = targetEntityId;
    }

    public String getTargetEntityType() {
        return targetEntityType;
    }

    public void setTargetEntityType(String targetEntityType) {
        this.targetEntityType = targetEntityType;
    }

    public String getDocumentType() {
        return documentType;
    }

    public void setDocumentType(String documentType) {
        this.documentType = documentType;
    }

    public String getStorageKey() {
        return storageKey;
    }

    public void setStorageKey(String storageKey) {
        this.storageKey = storageKey;
    }

    public String getDocumentTitle() {
        return documentTitle;
    }

    public void setDocumentTitle(String documentTitle) {
        this.documentTitle = documentTitle;
    }

    public String getMimeType() {
        return mimeType;
    }

    public void setMimeType(String mimeType) {
        this.mimeType = mimeType;
    }

    public long getFileSizeBytes() {
        return fileSizeBytes;
    }

    public void setFileSizeBytes(long fileSizeBytes) {
        this.fileSizeBytes = fileSizeBytes;
    }

    public String getSha256Checksum() {
        return sha256Checksum;
    }

    public void setSha256Checksum(String sha256Checksum) {
        this.sha256Checksum = sha256Checksum;
    }

    public String getGenerationAgentVersion() {
        return generationAgentVersion;
    }

    public void setGenerationAgentVersion(String generationAgentVersion) {
        this.generationAgentVersion = generationAgentVersion;
    }

    public boolean isValidated() {
        return validated;
    }

    public void setValidated(boolean validated) {
        this.validated = validated;
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
        DocumentDossierEntity that = (DocumentDossierEntity) o;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "DocumentDossierEntity{" +
                "id=" + id +
                ", targetEntityId='" + targetEntityId + '\'' +
                ", targetEntityType='" + targetEntityType + '\'' +
                ", documentType='" + documentType + '\'' +
                ", storageKey='" + storageKey + '\'' +
                ", documentTitle='" + documentTitle + '\'' +
                ", mimeType='" + mimeType + '\'' +
                ", validated=" + validated +
                ", createdAt=" + createdAt +
                '}';
    }
}
