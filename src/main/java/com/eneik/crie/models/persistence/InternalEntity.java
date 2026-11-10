package com.eneik.crie.models.persistence;

import java.io.Serializable;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * Persistence entity capturing generated document artifacts, SHA-256 provenance hashes,
 * generation parameters, and bidirectional academic entity relationships.
 */
public class InternalEntity implements Serializable, Comparable<InternalEntity> {

    private static final long serialVersionUID = 1L;

    private UUID id;
    private String documentType;
    private String title;
    private String author;
    private Instant timestamp;
    private String sha256Checksum;
    private List<String> sourceKnowledgeBaseReferences = new ArrayList<>();
    private List<String> targetEntityIds = new ArrayList<>();
    private Map<String, Object> generationParameters = new HashMap<>();
    private String artifactPath;
    private String content;
    private String postgraduateEntityId;
    private String departmentalEntityId;

    public InternalEntity() {
        this.id = UUID.randomUUID();
        this.timestamp = Instant.now();
    }

    public InternalEntity(UUID id,
                          String documentType,
                          String title,
                          String author,
                          Instant timestamp,
                          String sha256Checksum,
                          List<String> sourceKnowledgeBaseReferences,
                          List<String> targetEntityIds,
                          Map<String, Object> generationParameters,
                          String artifactPath,
                          String content,
                          String postgraduateEntityId,
                          String departmentalEntityId) {
        this.id = id != null ? id : UUID.randomUUID();
        this.documentType = documentType;
        this.title = title;
        this.author = author;
        this.timestamp = timestamp != null ? timestamp : Instant.now();
        this.sha256Checksum = sha256Checksum;
        if (sourceKnowledgeBaseReferences != null) {
            this.sourceKnowledgeBaseReferences = new ArrayList<>(sourceKnowledgeBaseReferences);
        }
        if (targetEntityIds != null) {
            this.targetEntityIds = new ArrayList<>(targetEntityIds);
        }
        if (generationParameters != null) {
            this.generationParameters = new HashMap<>(generationParameters);
        }
        this.artifactPath = artifactPath;
        this.content = content;
        this.postgraduateEntityId = postgraduateEntityId;
        this.departmentalEntityId = departmentalEntityId;

        if (this.sha256Checksum == null && content != null) {
            this.sha256Checksum = calculateSha256(content);
        }
    }

    public static String calculateSha256(String data) {
        if (data == null) {
            return null;
        }
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(data.getBytes(StandardCharsets.UTF_8));
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
            throw new IllegalStateException("SHA-256 algorithm not available", e);
        }
    }

    public boolean matchesEntity(String entityId) {
        if (entityId == null) {
            return false;
        }
        if (entityId.equals(postgraduateEntityId) || entityId.equals(departmentalEntityId)) {
            return true;
        }
        return targetEntityIds != null && targetEntityIds.contains(entityId);
    }

    @Override
    public int compareTo(InternalEntity other) {
        if (other == null || other.timestamp == null) {
            return this.timestamp == null ? 0 : -1;
        }
        if (this.timestamp == null) {
            return 1;
        }
        return other.timestamp.compareTo(this.timestamp);
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public String getDocumentType() {
        return documentType;
    }

    public void setDocumentType(String documentType) {
        this.documentType = documentType;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getAuthor() {
        return author;
    }

    public void setAuthor(String author) {
        this.author = author;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(Instant timestamp) {
        this.timestamp = timestamp;
    }

    public String getSha256Checksum() {
        return sha256Checksum;
    }

    public void setSha256Checksum(String sha256Checksum) {
        this.sha256Checksum = sha256Checksum;
    }

    public List<String> getSourceKnowledgeBaseReferences() {
        return sourceKnowledgeBaseReferences;
    }

    public void setSourceKnowledgeBaseReferences(List<String> sourceKnowledgeBaseReferences) {
        this.sourceKnowledgeBaseReferences = sourceKnowledgeBaseReferences != null
                ? new ArrayList<>(sourceKnowledgeBaseReferences)
                : new ArrayList<>();
    }

    public List<String> getTargetEntityIds() {
        return targetEntityIds;
    }

    public void setTargetEntityIds(List<String> targetEntityIds) {
        this.targetEntityIds = targetEntityIds != null
                ? new ArrayList<>(targetEntityIds)
                : new ArrayList<>();
    }

    public Map<String, Object> getGenerationParameters() {
        return generationParameters;
    }

    public void setGenerationParameters(Map<String, Object> generationParameters) {
        this.generationParameters = generationParameters != null
                ? new HashMap<>(generationParameters)
                : new HashMap<>();
    }

    public String getArtifactPath() {
        return artifactPath;
    }

    public void setArtifactPath(String artifactPath) {
        this.artifactPath = artifactPath;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
        if (content != null && (this.sha256Checksum == null || this.sha256Checksum.isEmpty())) {
            this.sha256Checksum = calculateSha256(content);
        }
    }

    public String getPostgraduateEntityId() {
        return postgraduateEntityId;
    }

    public void setPostgraduateEntityId(String postgraduateEntityId) {
        this.postgraduateEntityId = postgraduateEntityId;
    }

    public String getDepartmentalEntityId() {
        return departmentalEntityId;
    }

    public void setDepartmentalEntityId(String departmentalEntityId) {
        this.departmentalEntityId = departmentalEntityId;
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
                ", documentType='" + documentType + '\'' +
                ", title='" + title + '\'' +
                ", author='" + author + '\'' +
                ", timestamp=" + timestamp +
                ", sha256Checksum='" + sha256Checksum + '\'' +
                ", sourceKnowledgeBaseReferences=" + sourceKnowledgeBaseReferences +
                ", targetEntityIds=" + targetEntityIds +
                ", postgraduateEntityId='" + postgraduateEntityId + '\'' +
                ", departmentalEntityId='" + departmentalEntityId + '\'' +
                '}';
    }
}
