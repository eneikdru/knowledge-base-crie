import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from storage.normative_db import DEFAULT_DB_PATH, search_normative_documents, get_connection

app = FastAPI(
    title="CRIE Educational Assistant API",
    version="1.0.0",
    description="High-performance zero-dependency assistant API for FBUN CRIE educational center"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "db_ready": DEFAULT_DB_PATH.exists()}


@app.get("/api/normative/search")
def search_normative(
    q: str = Query(..., min_length=1, description="Search query (e.g. ФБУН, ГИА, ГЭК, Педиатрия)"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    limit: int = Query(25, ge=1, le=100)
):
    if not DEFAULT_DB_PATH.exists():
        raise HTTPException(status_code=503, detail="Normative database not yet initialized")
    return search_normative_documents(query=q, db_path=DEFAULT_DB_PATH, category_id=category_id, limit=limit)


@app.get("/api/normative/categories")
def list_categories():
    if not DEFAULT_DB_PATH.exists():
        return {"categories": []}
    conn = get_connection(DEFAULT_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, name, file_count FROM categories ORDER BY id ASC")
    cats = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"categories": cats, "total": len(cats)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
