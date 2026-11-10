package com.eneik.crie.models.persistence;

import java.io.Serializable;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * Persistent metadata entity representing generated institutional documents,
 * capturing SHA-256 provenance integrity checksums, source knowledge base references,
 * generation parameters, and bidirectional links to academic entities.
 */
public class DocumentMetadataEntity implements Serializable {

    private static final long serialVersionUID = 1L;

    private UUID id;
    private String title;
    private String documentType;
    private String author;
    private Instant createdAt;
    private Instant updatedAt;
    private String sha256Checksum;
    private String contentArtifactPath;
    private String artifactFormat;
    private String academicEntityId;
    private String departmentalEntityId;
    private List<String> sourceKnowledgeBaseReferences = new ArrayList<>();
    private List<String> targetEntityIds = new ArrayList<>();
    private Map<String, Object> generationParameters = new HashMap<>();
    private String status;

    public DocumentMetadataEntity() {
        this.id = UUID.randomUUID();
        this.createdAt = Instant.now();
        this.updatedAt = this.createdAt;
        this.status = "GENERATED";
    }

    public DocumentMetadataEntity(UUID id, String title, String documentType, String author,
                                  String sha256Checksum, String contentArtifactPath,
                                  String academicEntityId) {
        this.id = id != null ? id : UUID.randomUUID();
        this.title = title;
        this.documentType = documentType;
        this.author = author;
        this.sha256Checksum = sha256Checksum;
        this.contentArtifactPath = contentArtifactPath;
        this.academicEntityId = academicEntityId;
        this.createdAt = Instant.now();
        this.updatedAt = this.createdAt;
        this.status = "GENERATED";
    }

    public static String computeSha256(byte[] data) {
        if (data == null) {
            return null;
        }
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(data);
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) {
                    hexString.append('0');
                }
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 algorithm unavailable", e);
        }
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

    public Instant getTimestamp() {
        return createdAt;
    }

    public void setTimestamp(Instant timestamp) {
        this.createdAt = timestamp;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }

    public String getSha256Checksum() {
        return sha256Checksum;
    }

    public void setSha256Checksum(String sha256Checksum) {
        this.sha256Checksum = sha256Checksum;
    }

    public String getProvenanceHash() {
        return sha256Checksum;
    }

    public void setProvenanceHash(String provenanceHash) {
        this.sha256Checksum = provenanceHash;
    }

    public String getContentArtifactPath() {
        return contentArtifactPath;
    }

    public void setContentArtifactPath(String contentArtifactPath) {
        this.contentArtifactPath = contentArtifactPath;
    }

    public String getArtifactFormat() {
        return artifactFormat;
    }

    public void setArtifactFormat(String artifactFormat) {
        this.artifactFormat = artifactFormat;
    }

    public String getAcademicEntityId() {
        return academicEntityId;
    }

    public void setAcademicEntityId(String academicEntityId) {
        this.academicEntityId = academicEntityId;
    }

    public String getDepartmentalEntityId() {
        return departmentalEntityId;
    }

    public void setDepartmentalEntityId(String departmentalEntityId) {
        this.departmentalEntityId = departmentalEntityId;
    }

    public List<String> getSourceKnowledgeBaseReferences() {
        return sourceKnowledgeBaseReferences != null ? sourceKnowledgeBaseReferences : Collections.emptyList();
    }

    public void setSourceKnowledgeBaseReferences(List<String> sourceKnowledgeBaseReferences) {
        this.sourceKnowledgeBaseReferences = sourceKnowledgeBaseReferences != null ? new ArrayList<>(sourceKnowledgeBaseReferences) : new ArrayList<>();
    }

    public void addSourceKnowledgeBaseReference(String reference) {
        if (this.sourceKnowledgeBaseReferences == null) {
            this.sourceKnowledgeBaseReferences = new ArrayList<>();
        }
        if (reference != null && !this.sourceKnowledgeBaseReferences.contains(reference)) {
            this.sourceKnowledgeBaseReferences.add(reference);
        }
    }

    public List<String> getTargetEntityIds() {
        return targetEntityIds != null ? targetEntityIds : Collections.emptyList();
    }

    public void setTargetEntityIds(List<String> targetEntityIds) {
        this.targetEntityIds = targetEntityIds != null ? new ArrayList<>(targetEntityIds) : new ArrayList<>();
    }

    public void addTargetEntityId(String targetEntityId) {
        if (this.targetEntityIds == null) {
            this.targetEntityIds = new ArrayList<>();
        }
        if (targetEntityId != null && !this.targetEntityIds.contains(targetEntityId)) {
            this.targetEntityIds.add(targetEntityId);
        }
    }

    public Map<String, Object> getGenerationParameters() {
        return generationParameters != null ? generationParameters : Collections.emptyMap();
    }

    public void setGenerationParameters(Map<String, Object> generationParameters) {
        this.generationParameters = generationParameters != null ? new HashMap<>(generationParameters) : new HashMap<>();
    }

    public void addGenerationParameter(String key, Object value) {
        if (this.generationParameters == null) {
            this.generationParameters = new HashMap<>();
        }
        this.generationParameters.put(key, value);
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        DocumentMetadataEntity that = (DocumentMetadataEntity) o;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "DocumentMetadataEntity{" +
                "id=" + id +
                ", title='" + title + '\'' +
                ", documentType='" + documentType + '\'' +
                ", author='" + author + '\'' +
                ", createdAt=" + createdAt +
                ", sha256Checksum='" + sha256Checksum + '\'' +
                ", academicEntityId='" + academicEntityId + '\'' +
                ", status='" + status + '\'' +
                '}';
    }
}
