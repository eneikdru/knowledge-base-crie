# -*- coding: utf-8 -*-
"""
CRIE Feedback & Observations Manager
Persistently records, indexes and manages user remarks, bug reports,
and template feedback during pilot operation of the Educational Center system.
"""
import os
import json
import sqlite3
import csv
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

BASE_DIR = Path(__file__).resolve().parent
FEEDBACK_DIR = BASE_DIR / "data" / "feedback"
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = FEEDBACK_DIR / "feedback.db"
JSONL_PATH = FEEDBACK_DIR / "feedback.jsonl"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_feedback_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                author TEXT NOT NULL,
                role TEXT,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                feedback_text TEXT NOT NULL,
                expected_behavior TEXT,
                document_context TEXT,
                session_id TEXT,
                status TEXT DEFAULT 'new',
                admin_notes TEXT
            )
        """)
        conn.commit()


# Run DB initialization at module load
init_feedback_db()


def add_feedback(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Saves user feedback into both SQLite and JSONL append log.
    """
    created_at = datetime.now().isoformat()
    author = (entry.get("author") or "Сотрудник ОЦ").strip()
    role = (entry.get("role") or "Пользователь").strip()
    category = (entry.get("category") or "Общее замечание").strip()
    severity = (entry.get("severity") or "Важно").strip()
    feedback_text = (entry.get("feedback_text") or entry.get("text") or "").strip()
    expected_behavior = (entry.get("expected_behavior") or "").strip()
    document_context = (entry.get("document_context") or "").strip()
    session_id = (entry.get("session_id") or "").strip()
    status = "new"

    if not feedback_text:
        raise ValueError("Текст замечания не может быть пустым.")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_feedback (
                created_at, author, role, category, severity,
                feedback_text, expected_behavior, document_context, session_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            created_at, author, role, category, severity,
            feedback_text, expected_behavior, document_context, session_id, status
        ))
        conn.commit()
        feedback_id = cursor.lastrowid

    record = {
        "id": feedback_id,
        "created_at": created_at,
        "author": author,
        "role": role,
        "category": category,
        "severity": severity,
        "feedback_text": feedback_text,
        "expected_behavior": expected_behavior,
        "document_context": document_context,
        "session_id": session_id,
        "status": status,
        "admin_notes": ""
    }

    # Also append to JSONL log for human transparency & zero-data-loss
    try:
        with open(JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[FeedbackManager] Warning: failed to append JSONL: {e}")

    return record


def list_feedback(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    query = "SELECT * FROM user_feedback WHERE 1=1"
    params = []

    if status and status != "all":
        query += " AND status = ?"
        params.append(status)
    if category and category != "all":
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_feedback_stats() -> Dict[str, Any]:
    with get_db_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM user_feedback").fetchone()[0]
        by_status = dict(conn.execute("SELECT status, COUNT(*) FROM user_feedback GROUP BY status").fetchall())
        by_category = dict(conn.execute("SELECT category, COUNT(*) FROM user_feedback GROUP BY category").fetchall())
        by_severity = dict(conn.execute("SELECT severity, COUNT(*) FROM user_feedback GROUP BY severity").fetchall())

    return {
        "total": total,
        "by_status": by_status,
        "by_category": by_category,
        "by_severity": by_severity
    }


def update_feedback_status(feedback_id: int, status: str, admin_notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if admin_notes is not None:
            cursor.execute("""
                UPDATE user_feedback SET status = ?, admin_notes = ? WHERE id = ?
            """, (status, admin_notes, feedback_id))
        else:
            cursor.execute("""
                UPDATE user_feedback SET status = ? WHERE id = ?
            """, (status, feedback_id))
        conn.commit()

        row = cursor.execute("SELECT * FROM user_feedback WHERE id = ?", (feedback_id,)).fetchone()
        return dict(row) if row else None


def export_feedback_csv() -> str:
    items = list_feedback(limit=10000)
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow([
        "ID", "Дата и время", "Автор", "Должность/Роль", "Категория",
        "Важность", "Замечание", "Как должно быть", "Контекст документа", "Сессия", "Статус", "Заметки администратора"
    ])
    for item in items:
        writer.writerow([
            item.get("id"),
            item.get("created_at"),
            item.get("author"),
            item.get("role"),
            item.get("category"),
            item.get("severity"),
            item.get("feedback_text"),
            item.get("expected_behavior"),
            item.get("document_context"),
            item.get("session_id"),
            item.get("status"),
            item.get("admin_notes")
        ])
    return output.getvalue()
