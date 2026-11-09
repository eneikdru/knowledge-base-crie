package com.eneik.crie.models.persistence;

import java.io.Serializable;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * Persistence domain model for Academic Entity Graph Relational Schema.
 * Supports postgraduates, residents, supervisors, departments, commissions, and document links.
 * Implemented without external JPA annotations to maintain pure compatibility with current project classpath.
 */
public class InternalEntity implements Serializable {
    private static final long serialVersionUID = 1L;

    public enum EntityType {
        POSTGRADUATE,
        RESIDENT,
        APPLICANT,
        SUPERVISOR,
        DEPARTMENT,
        COMMISSION
    }

    public enum DocumentType {
        OFFICIAL_ORDER,
        DISSERTATION_PLAN,
        INDIVIDUAL_PLAN,
        ATTESTATION_REPORT,
        COMMISSION_PROTOCOL,
        SUPERVISOR_REVIEW
    }

    private String id;
    private EntityType entityType;
    private String externalRef;
    private String fullName;
    private String departmentId;
    private String supervisorId;
    private String commissionId;
    private String status;
    private Instant createdAt;
    private Instant updatedAt;
    private List<DocumentLink> documentLinks = new ArrayList<>();

    public InternalEntity() {
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    public InternalEntity(String id, EntityType entityType, String fullName) {
        this();
        this.id = id;
        this.entityType = entityType;
        this.fullName = fullName;
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

    public String getExternalRef() {
        return externalRef;
    }

    public void setExternalRef(String externalRef) {
        this.externalRef = externalRef;
    }

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
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

    public List<DocumentLink> getDocumentLinks() {
        return Collections.unmodifiableList(documentLinks);
    }

    public void addDocumentLink(DocumentLink link) {
        if (link != null) {
            link.setEntityId(this.id);
            this.documentLinks.add(link);
            this.updatedAt = Instant.now();
        }
    }

    public void removeDocumentLink(String documentId) {
        if (documentId != null) {
            this.documentLinks.removeIf(l -> Objects.equals(l.getDocumentId(), documentId));
            this.updatedAt = Instant.now();
        }
    }

    public static class DocumentLink implements Serializable {
        private static final long serialVersionUID = 1L;

        private String id;
        private String entityId;
        private String documentId;
        private DocumentType documentType;
        private String documentTitle;
        private String fileUri;
        private Instant linkedAt;
        private boolean validated;

        public DocumentLink() {
            this.linkedAt = Instant.now();
        }

        public DocumentLink(String id, String entityId, String documentId, DocumentType documentType, String documentTitle, String fileUri) {
            this();
            this.id = id;
            this.entityId = entityId;
            this.documentId = documentId;
            this.documentType = documentType;
            this.documentTitle = documentTitle;
            this.fileUri = fileUri;
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

        public String getDocumentId() {
            return documentId;
        }

        public void setDocumentId(String documentId) {
            this.documentId = documentId;
        }

        public DocumentType getDocumentType() {
            return documentType;
        }

        public void setDocumentType(DocumentType documentType) {
            this.documentType = documentType;
        }

        public String getDocumentTitle() {
            return documentTitle;
        }

        public void setDocumentTitle(String documentTitle) {
            this.documentTitle = documentTitle;
        }

        public String getFileUri() {
            return fileUri;
        }

        public void setFileUri(String fileUri) {
            this.fileUri = fileUri;
        }

        public Instant getLinkedAt() {
            return linkedAt;
        }

        public void setLinkedAt(Instant linkedAt) {
            this.linkedAt = linkedAt;
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
            DocumentLink that = (DocumentLink) o;
            return Objects.equals(id, that.id) || (Objects.equals(entityId, that.entityId) && Objects.equals(documentId, that.documentId));
        }

        @Override
        public int hashCode() {
            return Objects.hash(id, entityId, documentId);
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
