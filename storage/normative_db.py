import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DB_PATH = Path("data/normative_index.db")
MIGRATION_SQL_PATH = Path("db/migration/V20261108235230967__create_normative_documents_fts.sql")


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def initialize_schema(conn: sqlite3.Connection, migration_file: Path = MIGRATION_SQL_PATH) -> None:
    if migration_file.exists():
        sql_script = migration_file.read_text(encoding="utf-8")
        conn.executescript(sql_script)
    else:
        conn.executescript("""
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
        """)
    conn.commit()


def _extract_metadata_keywords(file_name: str, rel_path: str, category_name: str) -> Tuple[str, str]:
    title = Path(file_name).stem
    keywords_set = set()
    
    for term in ["ФБУН", "ЦНИИ", "ГЭК", "ГИА", "РПД", "РПП", "ОХОП", "ООП", "ФОС", "РУП", "ВЭ"]:
        if term.lower() in file_name.lower() or term.lower() in rel_path.lower():
            keywords_set.add(term)
            
    if "педиатри" in file_name.lower():
        keywords_set.add("Педиатрия")
    if "эпидемиолог" in file_name.lower():
        keywords_set.add("Эпидемиология")
    if "инфекционн" in file_name.lower():
        keywords_set.add("Инфекционные болезни")
    if "билет" in file_name.lower():
        keywords_set.add("Билеты")
    if "задач" in file_name.lower():
        keywords_set.add("Задачи")
    if "тест" in file_name.lower():
        keywords_set.add("Тесты")
        
    keywords = ", ".join(sorted(keywords_set))
    return title, keywords


def ingest_catalog_data(catalog_path: Path, db_path: Path = DEFAULT_DB_PATH) -> Dict[str, int]:
    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")
        
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)
        
    conn = get_connection(db_path)
    initialize_schema(conn)
    
    inserted_categories = 0
    inserted_documents = 0
    
    with conn:
        cursor = conn.cursor()
        categories_data = catalog.get("categories", [])
        
        for idx, cat_entry in enumerate(categories_data, start=1):
            cat_name = cat_entry.get("category", "")
            cat_code = f"CAT-{idx:03d}"
            file_count = cat_entry.get("file_count", len(cat_entry.get("files", [])))
            
            cursor.execute("""
                INSERT INTO categories (code, name, file_count)
                VALUES (?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    file_count = excluded.file_count
            """, (cat_code, cat_name, file_count))
            
            cursor.execute("SELECT id FROM categories WHERE code = ?", (cat_code,))
            cat_row = cursor.fetchone()
            cat_id = cat_row["id"]
            inserted_categories += 1
            
            for doc in cat_entry.get("files", []):
                file_name = doc.get("file_name", "")
                rel_path = doc.get("relative_path", "")
                extension = doc.get("extension", "").lower()
                size_bytes = doc.get("size_bytes", 0)
                
                title, keywords = _extract_metadata_keywords(file_name, rel_path, cat_name)
                content_text = f"{file_name} {title} {keywords} {cat_name} {rel_path}"
                
                cursor.execute("""
                    INSERT INTO normative_documents 
                    (category_id, file_name, relative_path, extension, size_bytes, title, keywords, content_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(relative_path) DO UPDATE SET
                        category_id = excluded.category_id,
                        file_name = excluded.file_name,
                        extension = excluded.extension,
                        size_bytes = excluded.size_bytes,
                        title = excluded.title,
                        keywords = excluded.keywords,
                        content_text = excluded.content_text,
                        updated_at = CURRENT_TIMESTAMP
                """, (cat_id, file_name, rel_path, extension, size_bytes, title, keywords, content_text))
                inserted_documents += 1
                
    conn.close()
    return {"categories_count": inserted_categories, "documents_count": inserted_documents}


def search_normative_documents(
    query: str,
    db_path: Path = DEFAULT_DB_PATH,
    category_id: Optional[int] = None,
    limit: int = 50
) -> Dict[str, Any]:
    start_time = time.perf_counter()
    clean_query = query.strip()
    
    if not clean_query:
        return {"query": query, "results": [], "count": 0, "duration_ms": 0.0}
        
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    tokens = [t.replace('"', '""') for t in clean_query.split() if t]
    if not tokens:
        conn.close()
        return {"query": query, "results": [], "count": 0, "duration_ms": 0.0}
        
    fts_query = " ".join(f'"{token}"*' for token in tokens)
    
    sql = """
        SELECT 
            doc.id,
            doc.category_id,
            c.code AS category_code,
            c.name AS category_name,
            doc.file_name,
            doc.relative_path,
            doc.extension,
            doc.size_bytes,
            doc.title,
            doc.keywords,
            snippet(normative_documents_fts, -1, '<b>', '</b>', '...', 10) AS match_snippet,
            bm25(normative_documents_fts) AS rank_score
        FROM normative_documents_fts
        JOIN normative_documents doc ON doc.id = normative_documents_fts.rowid
        JOIN categories c ON c.id = doc.category_id
        WHERE normative_documents_fts MATCH ?
    """
    params: List[Any] = [fts_query]
    
    if category_id is not None:
        sql += " AND doc.category_id = ?"
        params.append(category_id)
        
    sql += " ORDER BY rank_score ASC LIMIT ?"
    params.append(limit)
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "category_id": r["category_id"],
            "category_code": r["category_code"],
            "category_name": r["category_name"],
            "file_name": r["file_name"],
            "relative_path": r["relative_path"],
            "extension": r["extension"],
            "size_bytes": r["size_bytes"],
            "title": r["title"],
            "keywords": r["keywords"],
            "match_snippet": r["match_snippet"],
            "rank_score": float(r["rank_score"])
        })
        
    duration_ms = (time.perf_counter() - start_time) * 1000.0
    conn.close()
    
    return {
        "query": query,
        "results": results,
        "count": len(results),
        "duration_ms": round(duration_ms, 3)
    }


def explain_search_query_plan(query: str, db_path: Path = DEFAULT_DB_PATH) -> List[str]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    clean_query = query.strip()
    fts_query = f'"{clean_query}"*'
    
    sql = """
        EXPLAIN QUERY PLAN
        SELECT doc.id, doc.file_name
        FROM normative_documents_fts
        JOIN normative_documents doc ON doc.id = normative_documents_fts.rowid
        JOIN categories c ON c.id = doc.category_id
        WHERE normative_documents_fts MATCH ?
    """
    cursor.execute(sql, (fts_query,))
    plan_rows = cursor.fetchall()
    conn.close()
    return [dict(r)["detail"] for r in plan_rows]
