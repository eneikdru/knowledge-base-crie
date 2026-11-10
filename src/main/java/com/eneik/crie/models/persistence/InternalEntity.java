package com.eneik.crie.models.persistence;

import java.io.Serializable;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * Persistence domain model representing academic entities and their document link graphs
 * within the CRIE academic entity subsystem.
 */
public class InternalEntity implements Serializable {

    private static final long serialVersionUID = 1L;

    public enum EntityType {
        POSTGRADUATE,
        RESIDENT,
        APPLICANT,
        SUPERVISOR,
        DEPARTMENT,
        COMMISSION,
        OTHER
    }

    public static class DocumentLink implements Serializable {
        private static final long serialVersionUID = 1L;

        private String documentId;
        private String documentType;
        private String referenceUri;
        private Instant attachedAt;
        private Map<String, Object> metadata;

        public DocumentLink() {
            this.attachedAt = Instant.now();
            this.metadata = new HashMap<>();
        }

        public DocumentLink(String documentId, String documentType, String referenceUri) {
            this.documentId = documentId;
            this.documentType = documentType;
            this.referenceUri = referenceUri;
            this.attachedAt = Instant.now();
            this.metadata = new HashMap<>();
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

        public String getReferenceUri() {
            return referenceUri;
        }

        public void setReferenceUri(String referenceUri) {
            this.referenceUri = referenceUri;
        }

        public Instant getAttachedAt() {
            return attachedAt;
        }

        public void setAttachedAt(Instant attachedAt) {
            this.attachedAt = attachedAt;
        }

        public Map<String, Object> getMetadata() {
            return metadata;
        }

        public void setMetadata(Map<String, Object> metadata) {
            this.metadata = metadata != null ? metadata : new HashMap<>();
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            DocumentLink that = (DocumentLink) o;
            return Objects.equals(documentId, that.documentId);
        }

        @Override
        public int hashCode() {
            return Objects.hash(documentId);
        }

        @Override
        public String toString() {
            return "DocumentLink{" +
                    "documentId='" + documentId + '\'' +
                    ", documentType='" + documentType + '\'' +
                    ", referenceUri='" + referenceUri + '\'' +
                    ", attachedAt=" + attachedAt +
                    '}';
        }
    }

    private String id;
    private EntityType entityType;
    private String title;
    private String description;
    private String departmentId;
    private String supervisorId;
    private String commissionId;
    private String status;
    private Map<String, Object> metadata;
    private List<DocumentLink> documentLinks;
    private Instant createdAt;
    private Instant updatedAt;

    public InternalEntity() {
        this.id = UUID.randomUUID().toString();
        this.entityType = EntityType.OTHER;
        this.metadata = new HashMap<>();
        this.documentLinks = new ArrayList<>();
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
        this.status = "ACTIVE";
    }

    public InternalEntity(String id, EntityType entityType, String title) {
        this();
        if (id != null && !id.trim().isEmpty()) {
            this.id = id;
        }
        this.entityType = entityType != null ? entityType : EntityType.OTHER;
        this.title = title;
    }

    public void attachDocumentLink(DocumentLink link) {
        if (link == null || link.getDocumentId() == null) {
            return;
        }
        this.documentLinks.removeIf(existing -> Objects.equals(existing.getDocumentId(), link.getDocumentId()));
        this.documentLinks.add(link);
        this.updatedAt = Instant.now();
    }

    public boolean removeDocumentLink(String documentId) {
        if (documentId == null) {
            return false;
        }
        boolean removed = this.documentLinks.removeIf(existing -> Objects.equals(existing.getDocumentId(), documentId));
        if (removed) {
            this.updatedAt = Instant.now();
        }
        return removed;
    }

    public DocumentLink getDocumentLink(String documentId) {
        if (documentId == null) {
            return null;
        }
        for (DocumentLink link : this.documentLinks) {
            if (Objects.equals(link.getDocumentId(), documentId)) {
                return link;
            }
        }
        return null;
    }

    public boolean hasDocument(String documentId) {
        return getDocumentLink(documentId) != null;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public EntityType getEntityType() {
        return entityType;
    }

    public void setEntityType(EntityType entityType) {
        this.entityType = entityType;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public String getDepartmentId() {
        return departmentId;
    }

    public void setDepartmentId(String departmentId) {
        this.departmentId = departmentId;
    }

    public String getSupervisorId() {
        return supervisorId;
    }

    public void setSupervisorId(String supervisorId) {
        this.supervisorId = supervisorId;
    }

    public String getCommissionId() {
        return commissionId;
    }

    public void setCommissionId(String commissionId) {
        this.commissionId = commissionId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata != null ? metadata : new HashMap<>();
    }

    public List<DocumentLink> getDocumentLinks() {
        return Collections.unmodifiableList(documentLinks);
    }

    public void setDocumentLinks(List<DocumentLink> documentLinks) {
        this.documentLinks = documentLinks != null ? new ArrayList<>(documentLinks) : new ArrayList<>();
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

    @Override
    public String toString() {
        return "InternalEntity{" +
                "id='" + id + '\'' +
                ", entityType=" + entityType +
                ", title='" + title + '\'' +
                ", departmentId='" + departmentId + '\'' +
                ", supervisorId='" + supervisorId + '\'' +
                ", commissionId='" + commissionId + '\'' +
                ", status='" + status + '\'' +
                ", documentLinksCount=" + (documentLinks != null ? documentLinks.size() : 0) +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                '}';
    }
}
