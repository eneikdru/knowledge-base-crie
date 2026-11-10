-- V20261109224027906: Entity Document Linkage & Storage Integration
CREATE TABLE IF NOT EXISTS entity_document_links (
    id VARCHAR(64) NOT NULL PRIMARY KEY,
    entity_id VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    document_id VARCHAR(64) NOT NULL,
    storage_key VARCHAR(512) NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(64) NOT NULL,
    mime_type VARCHAR(128) NOT NULL DEFAULT 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    file_size_bytes BIGINT,
    dossier_category VARCHAR(64) DEFAULT 'OFFICIAL_DOSSIER',
    metadata_json TEXT,
    created_by VARCHAR(128),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entity_doc_links_entity ON entity_document_links(entity_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_entity_doc_links_storage ON entity_document_links(storage_key);
CREATE INDEX IF NOT EXISTS idx_entity_doc_links_doc_id ON entity_document_links(document_id);
