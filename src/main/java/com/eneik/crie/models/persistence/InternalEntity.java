package com.eneik.crie.models.persistence;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * Persistence model representing an internal academic entity card (resident, postgraduate,
 * applicant, academic supervisor, department, commission) and its linked official document dossier.
 */
public class InternalEntity {

    private UUID id;
    private String entityType;
    private String displayName;
    private String identifierCode;
    private List<DocumentLinkage> documentDossier;
    private Instant createdAt;
    private Instant updatedAt;
    private long version;

    public InternalEntity() {
        this.documentDossier = new ArrayList<>();
    }

    public InternalEntity(UUID id, String entityType, String displayName, String identifierCode) {
        this.id = id != null ? id : UUID.randomUUID();
        this.entityType = Objects.requireNonNull(entityType, "entityType must not be null");
        this.displayName = Objects.requireNonNull(displayName, "displayName must not be null");
        this.identifierCode = identifierCode;
        this.documentDossier = new ArrayList<>();
        this.createdAt = Instant.now();
        this.updatedAt = this.createdAt;
        this.version = 0L;
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public String getEntityType() {
        return entityType;
    }

    public void setEntityType(String entityType) {
        this.entityType = entityType;
    }

    public String getDisplayName() {
        return displayName;
    }

    public void setDisplayName(String displayName) {
        this.displayName = displayName;
    }

    public String getIdentifierCode() {
        return identifierCode;
    }

    public void setIdentifierCode(String identifierCode) {
        this.identifierCode = identifierCode;
    }

    public List<DocumentLinkage> getDocumentDossier() {
        return documentDossier != null ? Collections.unmodifiableList(documentDossier) : Collections.emptyList();
    }

    public void setDocumentDossier(List<DocumentLinkage> documentDossier) {
        this.documentDossier = documentDossier != null ? new ArrayList<>(documentDossier) : new ArrayList<>();
    }

    public void addDocumentLinkage(DocumentLinkage linkage) {
        Objects.requireNonNull(linkage, "DocumentLinkage must not be null");
        if (this.documentDossier == null) {
            this.documentDossier = new ArrayList<>();
        }
        this.documentDossier.add(linkage);
        this.updatedAt = Instant.now();
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

    public long getVersion() {
        return version;
    }

    public void setVersion(long version) {
        this.version = version;
    }

    /**
     * Represents an attached document record in the entity's official document dossier.
     */
    public static class DocumentLinkage {
        private UUID linkageId;
        private String storageKey;
        private String documentType;
        private String title;
        private String mimeType;
        private Instant linkedAt;
        private String generatedByAgentId;

        public DocumentLinkage() {
        }

        public DocumentLinkage(UUID linkageId, String storageKey, String documentType, String title, String mimeType, String generatedByAgentId) {
            this.linkageId = linkageId != null ? linkageId : UUID.randomUUID();
            this.storageKey = Objects.requireNonNull(storageKey, "storageKey must not be null");
            this.documentType = Objects.requireNonNull(documentType, "documentType must not be null");
            this.title = Objects.requireNonNull(title, "title must not be null");
            this.mimeType = mimeType != null ? mimeType : "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            this.linkedAt = Instant.now();
            this.generatedByAgentId = generatedByAgentId;
        }

        public UUID getLinkageId() {
            return linkageId;
        }

        public void setLinkageId(UUID linkageId) {
            this.linkageId = linkageId;
        }

        public String getStorageKey() {
            return storageKey;
        }

        public void setStorageKey(String storageKey) {
            this.storageKey = storageKey;
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

        public String getMimeType() {
            return mimeType;
        }

        public void setMimeType(String mimeType) {
            this.mimeType = mimeType;
        }

        public Instant getLinkedAt() {
            return linkedAt;
        }

        public void setLinkedAt(Instant linkedAt) {
            this.linkedAt = linkedAt;
        }

        public String getGeneratedByAgentId() {
            return generatedByAgentId;
        }

        public void setGeneratedByAgentId(String generatedByAgentId) {
            this.generatedByAgentId = generatedByAgentId;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            DocumentLinkage that = (DocumentLinkage) o;
            return Objects.equals(storageKey, that.storageKey) && Objects.equals(linkageId, that.linkageId);
        }

        @Override
        public int hashCode() {
            return Objects.hash(linkageId, storageKey);
        }
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
}
