CREATE TABLE IF NOT EXISTS corpus_catalog (
    id VARCHAR(64) PRIMARY KEY,
    category VARCHAR(64) NOT NULL,
    code VARCHAR(128) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    source_file VARCHAR(512),
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS corpus_document (
    id VARCHAR(64) PRIMARY KEY,
    catalog_id VARCHAR(64) NOT NULL,
    document_type VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content_text TEXT,
    metadata_json TEXT,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_corpus_document_catalog FOREIGN KEY (catalog_id) REFERENCES corpus_catalog(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_corpus_catalog_category ON corpus_catalog(category);
CREATE INDEX IF NOT EXISTS idx_corpus_document_catalog_id ON corpus_document(catalog_id);
