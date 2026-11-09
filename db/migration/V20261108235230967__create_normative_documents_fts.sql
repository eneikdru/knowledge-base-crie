-- Flyway Migration V20261108235230967: Zero-dependency indexed SQLite schema and FTS5 full-text search
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    file_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS normative_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    relative_path TEXT NOT NULL UNIQUE,
    extension TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    title TEXT,
    keywords TEXT,
    content_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_normative_documents_category_id ON normative_documents(category_id);
CREATE INDEX IF NOT EXISTS idx_normative_documents_file_name ON normative_documents(file_name);
CREATE INDEX IF NOT EXISTS idx_normative_documents_extension ON normative_documents(extension);

CREATE VIRTUAL TABLE IF NOT EXISTS normative_documents_fts USING fts5(
    file_name,
    title,
    keywords,
    content_text,
    category_name,
    content='normative_documents',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS trg_normative_documents_ai AFTER INSERT ON normative_documents BEGIN
    INSERT INTO normative_documents_fts(rowid, file_name, title, keywords, content_text, category_name)
    SELECT new.id, new.file_name, new.title, new.keywords, new.content_text, c.name
    FROM categories c WHERE c.id = new.category_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_normative_documents_ad AFTER DELETE ON normative_documents BEGIN
    INSERT INTO normative_documents_fts(normative_documents_fts, rowid, file_name, title, keywords, content_text, category_name)
    SELECT 'delete', old.id, old.file_name, old.title, old.keywords, old.content_text, c.name
    FROM categories c WHERE c.id = old.category_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_normative_documents_au AFTER UPDATE ON normative_documents BEGIN
    INSERT INTO normative_documents_fts(normative_documents_fts, rowid, file_name, title, keywords, content_text, category_name)
    SELECT 'delete', old.id, old.file_name, old.title, old.keywords, old.content_text, c.name
    FROM categories c WHERE c.id = old.category_id;
    INSERT INTO normative_documents_fts(rowid, file_name, title, keywords, content_text, category_name)
    SELECT new.id, new.file_name, new.title, new.keywords, new.content_text, c.name
    FROM categories c WHERE c.id = new.category_id;
END;
