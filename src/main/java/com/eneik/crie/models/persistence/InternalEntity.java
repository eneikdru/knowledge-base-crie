package com.eneik.crie.models.persistence;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Persistent entity capturing generated institutional document artifacts,
 * SHA-256 provenance hashes, generation parameters, and academic entity links.
 */
public class InternalEntity {

    private UUID id;
    private String title;
    private String documentType;
    private String author;
    private Instant createdAt;
    private String sha256Checksum;
    private String targetEntityId;
    private String departmentalEntityId;
    private String postgraduateEntityId;
    private List<String> sourceKnowledgeBaseReferences = new ArrayList<>();
    private Map<String, String> generationParameters = new HashMap<>();
    private String status;

    public InternalEntity() {
        this.id = UUID.randomUUID();
        this.createdAt = Instant.now();
        this.status = "DRAFT";
    }

    public InternalEntity(
            UUID id,
            String title,
            String documentType,
            String author,
            Instant createdAt,
            String sha256Checksum,
            String targetEntityId,
            String departmentalEntityId,
            String postgraduateEntityId,
            List<String> sourceKnowledgeBaseReferences,
            Map<String, String> generationParameters,
            String status
    ) {
        this.id = id != null ? id : UUID.randomUUID();
        this.title = title;
        this.documentType = documentType;
        this.author = author;
        this.createdAt = createdAt != null ? createdAt : Instant.now();
        this.sha256Checksum = sha256Checksum;
        this.targetEntityId = targetEntityId;
        this.departmentalEntityId = departmentalEntityId;
        this.postgraduateEntityId = postgraduateEntityId;
        if (sourceKnowledgeBaseReferences != null) {
            this.sourceKnowledgeBaseReferences = new ArrayList<>(sourceKnowledgeBaseReferences);
        }
        if (generationParameters != null) {
            this.generationParameters = new HashMap<>(generationParameters);
        }
        this.status = status != null ? status : "DRAFT";
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
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

    public String getAuthor() {
        return author;
    }

    public void setAuthor(String author) {
        this.author = author;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public String getSha256Checksum() {
        return sha256Checksum;
    }

    public void setSha256Checksum(String sha256Checksum) {
        this.sha256Checksum = sha256Checksum;
    }

    public String getTargetEntityId() {
        return targetEntityId;
    }

    public void setTargetEntityId(String targetEntityId) {
        this.targetEntityId = targetEntityId;
    }

    public String getDepartmentalEntityId() {
        return departmentalEntityId;
    }

    public void setDepartmentalEntityId(String departmentalEntityId) {
        this.departmentalEntityId = departmentalEntityId;
    }

    public String getPostgraduateEntityId() {
        return postgraduateEntityId;
    }

    public void setPostgraduateEntityId(String postgraduateEntityId) {
        this.postgraduateEntityId = postgraduateEntityId;
    }

    public List<String> getSourceKnowledgeBaseReferences() {
        return sourceKnowledgeBaseReferences;
    }

    public void setSourceKnowledgeBaseReferences(List<String> sourceKnowledgeBaseReferences) {
        this.sourceKnowledgeBaseReferences = sourceKnowledgeBaseReferences != null ? new ArrayList<>(sourceKnowledgeBaseReferences) : new ArrayList<>();
    }

    public Map<String, String> getGenerationParameters() {
        return generationParameters;
    }

    public void setGenerationParameters(Map<String, String> generationParameters) {
        this.generationParameters = generationParameters != null ? new HashMap<>(generationParameters) : new HashMap<>();
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
