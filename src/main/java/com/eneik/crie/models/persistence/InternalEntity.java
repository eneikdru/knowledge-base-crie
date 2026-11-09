package com.eneik.crie.models.persistence;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * Represents an entity card node within the CRIE academic entity graph
 * (e.g., resident, postgraduate, scientific supervisor, department, commission)
 * and its associated official document dossier.
 */
public class InternalEntity {

    private String id;
    private String entityType;
    private String displayName;
    private String department;
    private Instant createdAt;
    private Instant updatedAt;
    private List<DocumentLinkage> documentDossier = new ArrayList<>();

    public InternalEntity() {
    }

    public InternalEntity(String id, String entityType, String displayName, String department, Instant createdAt, Instant updatedAt) {
        this.id = id;
        this.entityType = entityType;
        this.displayName = displayName;
        this.department = department;
        this.createdAt = createdAt != null ? createdAt : Instant.now();
        this.updatedAt = updatedAt != null ? updatedAt : Instant.now();
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
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

    public String getDepartment() {
        return department;
    }

    public void setDepartment(String department) {
        this.department = department;
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

    public List<DocumentLinkage> getDocumentDossier() {
        return Collections.unmodifiableList(documentDossier);
    }

    public void setDocumentDossier(List<DocumentLinkage> documentDossier) {
        this.documentDossier = documentDossier != null ? new ArrayList<>(documentDossier) : new ArrayList<>();
    }

    public void addDocumentLinkage(DocumentLinkage linkage) {
        if (linkage != null) {
            this.documentDossier.add(linkage);
            this.updatedAt = Instant.now();
        }
    }

    public static class DocumentLinkage {
        private String storageKey;
        private String documentType;
        private String documentTitle;
        private String mimeType;
        private Instant generatedAt;
        private boolean validated;

        public DocumentLinkage() {
        }

        public DocumentLinkage(String storageKey, String documentType, String documentTitle, String mimeType, Instant generatedAt, boolean validated) {
            this.storageKey = storageKey;
            this.documentType = documentType;
            this.documentTitle = documentTitle;
            this.mimeType = mimeType;
            this.generatedAt = generatedAt != null ? generatedAt : Instant.now();
            this.validated = validated;
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

        public Instant getGeneratedAt() {
            return generatedAt;
        }

        public void setGeneratedAt(Instant generatedAt) {
            this.generatedAt = generatedAt;
        }

        public boolean isValidated() {
            return validated;
        }

        public void setValidated(boolean validated) {
            this.validated = validated;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            DocumentLinkage that = (DocumentLinkage) o;
            return validated == that.validated &&
                    Objects.equals(storageKey, that.storageKey) &&
                    Objects.equals(documentType, that.documentType) &&
                    Objects.equals(documentTitle, that.documentTitle) &&
                    Objects.equals(mimeType, that.mimeType);
        }

        @Override
        public int hashCode() {
            return Objects.hash(storageKey, documentType, documentTitle, mimeType, validated);
        }
    }
}
