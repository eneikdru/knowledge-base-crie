CREATE TABLE IF NOT EXISTS generated_documents (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    document_type VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content_artifact TEXT,
    sha256_checksum VARCHAR(64) NOT NULL,
    author VARCHAR(255) NOT NULL,
    target_entity_id VARCHAR(128) NOT NULL,
    entity_type VARCHAR(64),
    source_kb_refs TEXT,
    generation_parameters TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gen_docs_target_entity ON generated_documents(target_entity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gen_docs_sha256 ON generated_documents(sha256_checksum);
