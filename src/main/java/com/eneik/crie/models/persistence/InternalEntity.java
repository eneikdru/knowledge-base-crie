package com.eneik.crie.models.persistence;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Persistence entity representing an academic graph node (postgraduates, residents, supervisors, departments, commissions)
 * and its associated document references.
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

    private String id;
    private EntityType entityType;
    private String fullName;
    private String departmentId;
    private String supervisorId;
    private List<String> documentLinks = new ArrayList<>();
    private Map<String, String> attributes = new HashMap<>();
    private Instant createdAt;
    private Instant updatedAt;

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

    public List<String> getDocumentLinks() {
        return documentLinks;
    }

    public void setDocumentLinks(List<String> documentLinks) {
        this.documentLinks = documentLinks != null ? documentLinks : new ArrayList<>();
    }

    public void addDocumentLink(String documentId) {
        if (documentId != null && !this.documentLinks.contains(documentId)) {
            this.documentLinks.add(documentId);
            this.updatedAt = Instant.now();
        }
    }

    public Map<String, String> getAttributes() {
        return attributes;
    }

    public void setAttributes(Map<String, String> attributes) {
        this.attributes = attributes != null ? attributes : new HashMap<>();
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
}
