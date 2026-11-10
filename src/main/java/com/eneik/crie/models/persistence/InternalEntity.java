package com.eneik.crie.models.persistence;

import java.io.Serializable;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Persistence and domain model representing academic entities and relational graph links.
 * Supports postgraduates, residents, applicants, supervisors, departments, commissions,
 * and bidirectional document links under strict referential integrity.
 */
public class InternalEntity implements Serializable {

    private static final long serialVersionUID = 1L;

    public static final String TABLE_ACADEMIC_ENTITIES = "academic_entities";
    public static final String TABLE_SUPERVISORS = "supervisors";
    public static final String TABLE_DEPARTMENTS = "departments";
    public static final String TABLE_COMMISSIONS = "commissions";
    public static final String TABLE_ENTITY_DOCUMENT_LINKS = "entity_document_links";

    public enum EntityType {
        POSTGRADUATE,
        RESIDENT,
        APPLICANT,
        SUPERVISOR,
        DEPARTMENT,
        COMMISSION,
        OTHER
    }

    private String id;
    private String name;
    private String entityType;
    private String departmentId;
    private String supervisorId;
    private String commissionId;
    private String documentReference;
    private String status;
    private Map<String, Object> metadata = new HashMap<>();
    private final List<DocumentLink> documentLinks = new CopyOnWriteArrayList<>();
    private Instant createdAt;
    private Instant updatedAt;

    public InternalEntity() {
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    public InternalEntity(String id, String name) {
        this();
        this.id = id;
        this.name = name;
    }

    public InternalEntity(String id, String name, String entityType) {
        this(id, name);
        this.entityType = entityType;
    }

    public InternalEntity(String id, String name, EntityType entityType) {
        this(id, name);
        this.entityType = entityType != null ? entityType.name() : null;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public void setId(Long id) {
        this.id = id != null ? id.toString() : null;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getEntityType() {
        return entityType;
    }

    public void setEntityType(String entityType) {
        this.entityType = entityType;
    }

    public void setEntityType(EntityType type) {
        this.entityType = type != null ? type.name() : null;
    }

    public String getType() {
        return entityType;
    }

    public void setType(String type) {
        this.entityType = type;
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

    public String getDocumentReference() {
        return documentReference;
    }

    public void setDocumentReference(String documentReference) {
        this.documentReference = documentReference;
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
        this.metadata = metadata != null ? new HashMap<>(metadata) : new HashMap<>();
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

    public void setDocumentLinks(List<DocumentLink> links) {
        this.documentLinks.clear();
        if (links != null) {
            this.documentLinks.addAll(links);
        }
    }

    public void addDocumentLink(DocumentLink link) {
        if (link != null) {
            if (link.getEntityId() == null && this.id != null) {
                link.setEntityId(this.id);
            }
            this.documentLinks.add(link);
        }
    }

    public void removeDocumentLink(String linkId) {
        if (linkId != null) {
            this.documentLinks.removeIf(l -> Objects.equals(l.getId(), linkId));
        }
    }

    public List<DocumentLink> findLinksByDocumentReference(String docRef) {
        if (docRef == null) {
            return Collections.emptyList();
        }
        List<DocumentLink> result = new ArrayList<>();
        for (DocumentLink link : documentLinks) {
            if (docRef.equals(link.getDocumentReference())) {
                result.add(link);
            }
        }
        return result;
    }

    public static class DocumentLink implements Serializable {
        private static final long serialVersionUID = 1L;

        private String id;
        private String entityId;
        private String documentReference;
        private String documentType;
        private Instant linkedAt;

        public DocumentLink() {
            this.linkedAt = Instant.now();
        }

        public DocumentLink(String id, String entityId, String documentReference, String documentType) {
            this();
            this.id = id;
            this.entityId = entityId;
            this.documentReference = documentReference;
            this.documentType = documentType;
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

        public String getDocumentReference() {
            return documentReference;
        }

        public void setDocumentReference(String documentReference) {
            this.documentReference = documentReference;
        }

        public String getDocumentType() {
            return documentType;
        }

        public void setDocumentType(String documentType) {
            this.documentType = documentType;
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
            return Objects.equals(id, that.id) &&
                    Objects.equals(entityId, that.entityId) &&
                    Objects.equals(documentReference, that.documentReference);
        }

        @Override
        public int hashCode() {
            return Objects.hash(id, entityId, documentReference);
        }

        @Override
        public String toString() {
            return "DocumentLink{" +
                    "id='" + id + '\'' +
                    ", entityId='" + entityId + '\'' +
                    ", documentReference='" + documentReference + '\'' +
                    ", documentType='" + documentType + '\'' +
                    ", linkedAt=" + linkedAt +
                    '}';
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

    @Override
    public String toString() {
        return "InternalEntity{" +
                "id='" + id + '\'' +
                ", name='" + name + '\'' +
                ", entityType='" + entityType + '\'' +
                ", departmentId='" + departmentId + '\'' +
                ", supervisorId='" + supervisorId + '\'' +
                ", commissionId='" + commissionId + '\'' +
                ", documentReference='" + documentReference + '\'' +
                ", status='" + status + '\'' +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                '}';
    }
}
