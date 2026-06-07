"""
Persistent storage for conversations using SQLite.

Automatically saves conversations as they are modified and
restores them on application startup.
"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from core.conversation import Conversation, ConversationEntry

DB_PATH = Path.home() / ".ai_assistant" / "conversations.db"


class ConversationStorage:
    """SQLite-backed storage for conversations."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self._lock = threading.Lock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA foreign_keys=ON")
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL DEFAULT 'New conversation',
                        system_prompt TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL DEFAULT '',
                        timestamp TEXT NOT NULL,
                        tool_calls TEXT,
                        tool_call_id TEXT,
                        files TEXT,
                        tokens INTEGER DEFAULT 0,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                    );

                    CREATE INDEX IF NOT EXISTS idx_messages_conv
                        ON messages(conversation_id, timestamp);
                """)
            finally:
                conn.close()

    def save_conversation(self, conv: Conversation) -> None:
        """Save or update a conversation and all its messages."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                now = datetime.now().isoformat()
                conn.execute(
                    """INSERT OR REPLACE INTO conversations
                       (id, title, system_prompt, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (conv.id, conv.title, conv.system_prompt, conv.created_at, now),
                )

                conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv.id,))
                with conv._lock:
                    entries = list(conv.entries)
                for entry in entries:
                    conn.execute(
                        """INSERT INTO messages
                           (id, conversation_id, role, content, timestamp,
                            tool_calls, tool_call_id, files, tokens)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            entry.id,
                            conv.id,
                            entry.role,
                            entry.content,
                            entry.timestamp,
                            json.dumps(entry.tool_calls) if entry.tool_calls else None,
                            entry.tool_call_id,
                            json.dumps(entry.files) if entry.files else None,
                            entry.tokens,
                        ),
                    )
                conn.commit()
            finally:
                conn.close()

    def load_conversation(self, conv_id: str) -> Conversation | None:
        """Load a single conversation with all its messages."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                row = conn.execute(
                    "SELECT id, title, system_prompt, created_at FROM conversations WHERE id = ?",
                    (conv_id,),
                ).fetchone()
                if not row:
                    return None

                conv = Conversation(system_prompt=row[3] or "")
                conv.id = row[0]
                conv.title = row[1]
                conv.system_prompt = row[2] or ""
                conv.created_at = row[3]

                msg_rows = conn.execute(
                    "SELECT id, role, content, timestamp, tool_calls, tool_call_id, files, tokens "
                    "FROM messages WHERE conversation_id = ? ORDER BY timestamp",
                    (conv_id,),
                ).fetchall()

                for mrow in msg_rows:
                    try:
                        tool_calls = json.loads(mrow[4]) if mrow[4] else None
                    except json.JSONDecodeError, TypeError:
                        tool_calls = None
                    try:
                        files = json.loads(mrow[6]) if mrow[6] else []
                    except json.JSONDecodeError, TypeError:
                        files = []
                    entry = ConversationEntry(
                        id=mrow[0],
                        role=mrow[1],
                        content=mrow[2],
                        timestamp=mrow[3],
                        tool_calls=tool_calls,
                        tool_call_id=mrow[5],
                        files=files,
                        tokens=mrow[7] or 0,
                    )
                    conv.entries.append(entry)

                return conv
            finally:
                conn.close()

    def list_conversations(self) -> list[dict[str, Any]]:
        """List all conversations summary (id, title, created_at, message_count)."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                rows = conn.execute(
                    """SELECT c.id, c.title, c.created_at, c.updated_at,
                              COUNT(m.id) as msg_count
                       FROM conversations c
                       LEFT JOIN messages m ON m.conversation_id = c.id
                       GROUP BY c.id
                       ORDER BY c.updated_at DESC"""
                ).fetchall()
                return [
                    {
                        "id": r[0],
                        "title": r[1],
                        "created_at": r[2],
                        "updated_at": r[3],
                        "message_count": r[4],
                    }
                    for r in rows
                ]
            finally:
                conn.close()

    def delete_conversation(self, conv_id: str) -> None:
        """Delete a conversation and its messages."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
                conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
                conn.commit()
            finally:
                conn.close()

    def update_title(self, conv_id: str, title: str) -> None:
        """Update a conversation title."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute(
                    "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                    (title, datetime.now().isoformat(), conv_id),
                )
                conn.commit()
            finally:
                conn.close()
