package com.eneik.crie.models.persistence;

import java.io.Serializable;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * Represents an academic entity card (resident, postgraduate, applicant, supervisor,
 * department, commission) and its document graph linkage in the CRIE system.
 */
public class InternalEntity implements Serializable {

    private static final long serialVersionUID = 1L;

    private String id;
    private String entityType;
    private String fullName;
    private String department;
    private String academicRank;
    private List<DocumentLink> linkedDocuments = new ArrayList<>();
    private Instant createdAt;
    private Instant updatedAt;

    public InternalEntity() {
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    public InternalEntity(String id, String entityType, String fullName, String department, String academicRank) {
        this.id = id;
        this.entityType = entityType;
        this.fullName = fullName;
        this.department = department;
        this.academicRank = academicRank;
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
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

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }

    public String getDepartment() {
        return department;
    }

    public void setDepartment(String department) {
        this.department = department;
    }

    public String getAcademicRank() {
        return academicRank;
    }

    public void setAcademicRank(String academicRank) {
        this.academicRank = academicRank;
    }

    public List<DocumentLink> getLinkedDocuments() {
        return Collections.unmodifiableList(linkedDocuments);
    }

    public void setLinkedDocuments(List<DocumentLink> linkedDocuments) {
        this.linkedDocuments = (linkedDocuments != null) ? new ArrayList<>(linkedDocuments) : new ArrayList<>();
    }

    public void addDocumentLink(DocumentLink link) {
        if (link != null) {
            this.linkedDocuments.add(link);
            this.updatedAt = Instant.now();
        }
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
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    /**
     * Represents a permanent storage key and metadata linkage to an administrative
     * or official order document (e.g. docx).
     */
    public static class DocumentLink implements Serializable {
        private static final long serialVersionUID = 1L;

        private String documentId;
        private String title;
        private String documentType;
        private String storageKey;
        private String mimeType;
        private Instant linkedAt;

        public DocumentLink() {
            this.linkedAt = Instant.now();
        }

        public DocumentLink(String documentId, String title, String documentType, String storageKey, String mimeType) {
            this.documentId = documentId;
            this.title = title;
            this.documentType = documentType;
            this.storageKey = storageKey;
            this.mimeType = mimeType;
            this.linkedAt = Instant.now();
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

        public String getStorageKey() {
            return storageKey;
        }

        public void setStorageKey(String storageKey) {
            this.storageKey = storageKey;
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

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            DocumentLink that = (DocumentLink) o;
            return Objects.equals(documentId, that.documentId) &&
                    Objects.equals(storageKey, that.storageKey);
        }

        @Override
        public int hashCode() {
            return Objects.hash(documentId, storageKey);
        }
    }
}
