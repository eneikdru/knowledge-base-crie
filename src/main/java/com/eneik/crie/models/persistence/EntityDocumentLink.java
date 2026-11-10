package com.eneik.crie.models.persistence;

import java.io.Serializable;
import java.time.Instant;
import java.util.Objects;

/**
 * Represents a link between an administrative entity card (resident, supervisor, aspirant, department)
 * and a generated/stored administrative document (e.g. DOCX official order).
 */
public class EntityDocumentLink implements Serializable {

    private static final long serialVersionUID = 1L;

    private String id;
    private String entityId;
    private String entityType;
    private String documentId;
    private String storageKey;
    private String documentName;
    private String documentType;
    private String mimeType;
    private Long fileSizeBytes;
    private String dossierCategory;
    private String metadataJson;
    private String createdBy;
    private Instant createdAt;

    public EntityDocumentLink() {
        this.mimeType = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
        this.dossierCategory = "OFFICIAL_DOSSIER";
        this.createdAt = Instant.now();
    }

    public EntityDocumentLink(String id,
                              String entityId,
                              String entityType,
                              String documentId,
                              String storageKey,
                              String documentName,
                              String documentType,
                              String mimeType,
                              Long fileSizeBytes,
                              String dossierCategory,
                              String metadataJson,
                              String createdBy,
                              Instant createdAt) {
        this.id = id;
        this.entityId = entityId;
        this.entityType = entityType;
        this.documentId = documentId;
        this.storageKey = storageKey;
        this.documentName = documentName;
        this.documentType = documentType;
        this.mimeType = mimeType != null ? mimeType : "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
        this.fileSizeBytes = fileSizeBytes;
        this.dossierCategory = dossierCategory != null ? dossierCategory : "OFFICIAL_DOSSIER";
        this.metadataJson = metadataJson;
        this.createdBy = createdBy;
        this.createdAt = createdAt != null ? createdAt : Instant.now();
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getEntityId() {
        return entityId;
    }

    public void setEntityId(String entityId) {
        this.entityId = entityId;
    }

    public String getEntityType() {
        return entityType;
    }

    public void setEntityType(String entityType) {
        this.entityType = entityType;
    }

    public String getDocumentId() {
        return documentId;
    }

    public void setDocumentId(String documentId) {
        this.documentId = documentId;
    }

    public String getStorageKey() {
        return storageKey;
    }

    public void setStorageKey(String storageKey) {
        this.storageKey = storageKey;
    }

    public String getDocumentName() {
        return documentName;
    }

    public void setDocumentName(String documentName) {
        this.documentName = documentName;
    }

    public String getDocumentType() {
        return documentType;
    }

    public void setDocumentType(String documentType) {
        this.documentType = documentType;
    }

    public String getMimeType() {
        return mimeType;
    }

    public void setMimeType(String mimeType) {
        this.mimeType = mimeType;
    }

    public Long getFileSizeBytes() {
        return fileSizeBytes;
    }

    public void setFileSizeBytes(Long fileSizeBytes) {
        this.fileSizeBytes = fileSizeBytes;
    }

    public String getDossierCategory() {
        return dossierCategory;
    }

    public void setDossierCategory(String dossierCategory) {
        this.dossierCategory = dossierCategory;
    }

    public String getMetadataJson() {
        return metadataJson;
    }

    public void setMetadataJson(String metadataJson) {
        this.metadataJson = metadataJson;
    }

    public String getCreatedBy() {
        return createdBy;
    }

    public void setCreatedBy(String createdBy) {
        this.createdBy = createdBy;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        EntityDocumentLink that = (EntityDocumentLink) o;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "EntityDocumentLink{" +
                "id='" + id + '\'' +
                ", entityId='" + entityId + '\'' +
                ", entityType='" + entityType + '\'' +
                ", documentId='" + documentId + '\'' +
                ", storageKey='" + storageKey + '\'' +
                ", documentName='" + documentName + '\'' +
                ", documentType='" + documentType + '\'' +
                ", mimeType='" + mimeType + '\'' +
                ", fileSizeBytes=" + fileSizeBytes +
                ", dossierCategory='" + dossierCategory + '\'' +
                ", createdBy='" + createdBy + '\'' +
                ", createdAt=" + createdAt +
                '}';
    }
}
