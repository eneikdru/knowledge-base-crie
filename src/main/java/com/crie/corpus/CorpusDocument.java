package com.crie.corpus;

import java.time.Instant;
import java.util.Objects;

public class CorpusDocument {
    private final String id;
    private final String catalogId;
    private final CorpusCategory category;
    private final String title;
    private final String content;
    private final String sourcePath;
    private final CorpusStatus status;
    private final Instant createdAt;

    public CorpusDocument(String id, String catalogId, CorpusCategory category, String title, String content, String sourcePath, CorpusStatus status, Instant createdAt) {
        this.id = Objects.requireNonNull(id, "id must not be null");
        this.catalogId = Objects.requireNonNull(catalogId, "catalogId must not be null");
        this.category = Objects.requireNonNull(category, "category must not be null");
        this.title = Objects.requireNonNull(title, "title must not be null");
        this.content = content != null ? content : "";
        this.sourcePath = sourcePath;
        this.status = Objects.requireNonNull(status, "status must not be null");
        this.createdAt = createdAt != null ? createdAt : Instant.now();
    }

    public String getId() { return id; }
    public String getCatalogId() { return catalogId; }
    public CorpusCategory getCategory() { return category; }
    public String getTitle() { return title; }
    public String getContent() { return content; }
    public String getSourcePath() { return sourcePath; }
    public CorpusStatus getStatus() { return status; }
    public Instant getCreatedAt() { return createdAt; }
}
