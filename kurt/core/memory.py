"""
KURT Memory - Nag-reremember ng conversations
SQLite-based, local, private
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path


KURT_DIR = Path.home() / ".kurt"
DB_PATH = KURT_DIR / "memory.db"


def init_db():
    """Initialize the memory database"""
    KURT_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            model TEXT,
            task_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_message(session_id: str, role: str, content: str,
                  model: str = None, task_type: str = None):
    """Save a message to memory"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO conversations (session_id, role, content, model, task_type)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, role, content, model, task_type))

    # Update session
    cursor.execute("""
        INSERT OR REPLACE INTO sessions (id, title, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (session_id, f"Session {session_id[:8]}"))

    conn.commit()
    conn.close()


def get_history(session_id: str, limit: int = 20) -> list:
    """Get conversation history for a session"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT role, content FROM conversations
        WHERE session_id = ?
        ORDER BY timestamp DESC, id DESC
        LIMIT ?
    """, (session_id, limit))

    rows = cursor.fetchall()
    conn.close()

    # Reverse to get chronological order
    messages = [{"role": row[0], "content": row[1]} for row in reversed(rows)]
    return messages


def list_sessions(limit: int = 10) -> list:
    """List recent sessions"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, updated_at FROM sessions
        ORDER BY updated_at DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [{"id": r[0], "title": r[1], "updated_at": r[2]} for r in rows]


def clear_session(session_id: str):
    """Clear a specific session"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
