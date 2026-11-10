package com.eneik.crie.models.persistence;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * Represents an academic entity record within the academic graph relational schema.
 * Supports postgraduates, residents, supervisors, departments, commissions,
 * and their associated document links.
 */
public class InternalEntity {

    public enum EntityType {
        POSTGRADUATE,
        RESIDENT,
        APPLICANT,
        SUPERVISOR,
        DEPARTMENT,
        COMMISSION
    }

    public enum EntityStatus {
        DRAFT,
        ACTIVE,
        ARCHIVED,
        SUSPENDED
    }

    private UUID id;
    private String externalId;
    private EntityType entityType;
    private String title;
    private String fullName;
    private String departmentCode;
    private UUID parentEntityId;
    private EntityStatus status;
    private List<String> documentLinks;
    private String metadataJson;
    private Instant createdAt;
    private Instant updatedAt;
    private Long version;

    public InternalEntity() {
        this.id = UUID.randomUUID();
        this.status = EntityStatus.DRAFT;
        this.documentLinks = new ArrayList<>();
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
        this.version = 0L;
    }

    public InternalEntity(UUID id, EntityType entityType, String fullName, String departmentCode) {
        this.id = id != null ? id : UUID.randomUUID();
        this.entityType = entityType;
        this.fullName = fullName;
        this.departmentCode = departmentCode;
        this.status = EntityStatus.ACTIVE;
        this.documentLinks = new ArrayList<>();
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
        this.version = 0L;
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public String getExternalId() {
        return externalId;
    }

    public void setExternalId(String externalId) {
        this.externalId = externalId;
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

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }

    public String getDepartmentCode() {
        return departmentCode;
    }

    public void setDepartmentCode(String departmentCode) {
        this.departmentCode = departmentCode;
    }

    public UUID getParentEntityId() {
        return parentEntityId;
    }

    public void setParentEntityId(UUID parentEntityId) {
        this.parentEntityId = parentEntityId;
    }

    public EntityStatus getStatus() {
        return status;
    }

    public void setStatus(EntityStatus status) {
        this.status = status;
    }

    public List<String> getDocumentLinks() {
        return documentLinks;
    }

    public void setDocumentLinks(List<String> documentLinks) {
        this.documentLinks = documentLinks != null ? documentLinks : new ArrayList<>();
    }

    public void addDocumentLink(String documentLink) {
        if (documentLink != null && !this.documentLinks.contains(documentLink)) {
            this.documentLinks.add(documentLink);
        }
    }

    public String getMetadataJson() {
        return metadataJson;
    }

    public void setMetadataJson(String metadataJson) {
        this.metadataJson = metadataJson;
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

    public Long getVersion() {
        return version;
    }

    public void setVersion(Long version) {
        this.version = version;
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
                "id=" + id +
                ", externalId='" + externalId + '\'' +
                ", entityType=" + entityType +
                ", fullName='" + fullName + '\'' +
                ", departmentCode='" + departmentCode + '\'' +
                ", status=" + status +
                ", documentLinksCount=" + (documentLinks != null ? documentLinks.size() : 0) +
                ", version=" + version +
                '}';
    }
}
