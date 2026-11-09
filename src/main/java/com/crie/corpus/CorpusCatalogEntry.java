package com.crie.corpus;

import java.time.Instant;

public class CorpusCatalogEntry {
    private final String id;
    private final CorpusCategory category;
    private final String code;
    private final String title;
    private final String sourceFile;
    private final CorpusStatus status;
    private final Instant createdAt;

    public CorpusCatalogEntry(String id, CorpusCategory category, String code, String title, String sourceFile, CorpusStatus status, Instant createdAt) {
        this.id = id;
        this.category = category;
        this.code = code;
        this.title = title;
        this.sourceFile = sourceFile;
        this.status = status;
        this.createdAt = createdAt != null ? createdAt : Instant.now();
    }

    public String getId() { return id; }
    public CorpusCategory getCategory() { return category; }
    public String getCode() { return code; }
    public String getTitle() { return title; }
    public String getSourceFile() { return sourceFile; }
    public CorpusStatus getStatus() { return status; }
    public Instant getCreatedAt() { return createdAt; }
}
