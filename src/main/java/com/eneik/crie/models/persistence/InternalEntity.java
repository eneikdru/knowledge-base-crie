package com.eneik.crie.models.persistence;

import java.io.Serializable;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * Persistence entity representing an entity card and its official document dossier
 * within the academic entity relationship graph.
 */
public class InternalEntity implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;
    private String entityCardId;
    private String entityType;
    private String displayName;
    private Long version;
    private Instant createdAt;
    private Instant updatedAt;
    private List<DocumentDossierEntry> documentDossier = new ArrayList<>();

    public InternalEntity() {
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
        this.version = 0L;
    }

    public InternalEntity(String entityCardId, String entityType, String displayName) {
        this();
        this.entityCardId = entityCardId;
        this.entityType = entityType;
        this.displayName = displayName;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getEntityCardId() {
        return entityCardId;
    }

    public void setEntityCardId(String entityCardId) {
        this.entityCardId = entityCardId;
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

    public Long getVersion() {
        return version;
    }

    public void setVersion(Long version) {
        this.version = version;
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

    public List<DocumentDossierEntry> getDocumentDossier() {
        return Collections.unmodifiableList(documentDossier);
    }

    public void setDocumentDossier(List<DocumentDossierEntry> documentDossier) {
        this.documentDossier = documentDossier != null ? new ArrayList<>(documentDossier) : new ArrayList<>();
    }

    public synchronized void addDocument(DocumentDossierEntry document) {
        if (document != null) {
            this.documentDossier.add(document);
            this.updatedAt = Instant.now();
        }
    }

    public synchronized boolean removeDocument(String storageKey) {
        if (storageKey == null) {
            return false;
        }
        boolean removed = this.documentDossier.removeIf(doc -> storageKey.equals(doc.getStorageKey()));
        if (removed) {
            this.updatedAt = Instant.now();
        }
        return removed;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        InternalEntity that = (InternalEntity) o;
        return Objects.equals(id, that.id) && Objects.equals(entityCardId, that.entityCardId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, entityCardId);
    }

    @Override
    public String toString() {
        return "InternalEntity{" +
                "id=" + id +
                ", entityCardId='" + entityCardId + '\'' +
                ", entityType='" + entityType + '\'' +
                ", displayName='" + displayName + '\'' +
                ", version=" + version +
                ", documentCount=" + documentDossier.size() +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                '}';
    }

    /**
     * Represents a permanent official document linkage entry in an entity card's dossier.
     */
    public static class DocumentDossierEntry implements Serializable {
        private static final long serialVersionUID = 1L;

        private String documentId;
        private String title;
        private String documentType;
        private String mimeType;
        private String storageKey;
        private Instant generatedAt;
        private String verificationChecksum;

        public DocumentDossierEntry() {
            this.generatedAt = Instant.now();
        }

        public DocumentDossierEntry(String documentId, String title, String documentType, String mimeType, String storageKey, String verificationChecksum) {
            this.documentId = documentId;
            this.title = title;
            this.documentType = documentType;
            this.mimeType = mimeType;
            this.storageKey = storageKey;
            this.verificationChecksum = verificationChecksum;
            this.generatedAt = Instant.now();
        }

        public String getDocumentId() {
            return documentId;
        }

        public void setDocumentId(String documentId) {
            this.documentId = documentId;
        }

        public String getTitle() {
            return title;
        }

        public void setTitle(String title) {
            this.title = title;
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

        public String getStorageKey() {
            return storageKey;
        }

        public void setStorageKey(String storageKey) {
            this.storageKey = storageKey;
        }

        public Instant getGeneratedAt() {
            return generatedAt;
        }

        public void setGeneratedAt(Instant generatedAt) {
            this.generatedAt = generatedAt;
        }

        public String getVerificationChecksum() {
            return verificationChecksum;
        }

        public void setVerificationChecksum(String verificationChecksum) {
            this.verificationChecksum = verificationChecksum;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            DocumentDossierEntry that = (DocumentDossierEntry) o;
            return Objects.equals(storageKey, that.storageKey);
        }

        @Override
        public int hashCode() {
            return Objects.hash(storageKey);
        }

        @Override
        public String toString() {
            return "DocumentDossierEntry{" +
                    "documentId='" + documentId + '\'' +
                    ", title='" + title + '\'' +
                    ", documentType='" + documentType + '\'' +
                    ", mimeType='" + mimeType + '\'' +
                    ", storageKey='" + storageKey + '\'' +
                    ", generatedAt=" + generatedAt +
                    '}';
        }
    }
}
