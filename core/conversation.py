"""
Conversation manager - handles chat history and thread management.

Stores messages, manages context window limits, and provides
serialization/deserialization for saving conversations.
"""

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.providers.base import Message


@dataclass
class ConversationEntry:
    """A single entry in conversation history with metadata."""

    id: str
    role: str
    content: str
    timestamp: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    files: list[str] = field(default_factory=list)
    tokens: int = 0


class Conversation:
    """Manages a single conversation thread."""

    def __init__(self, system_prompt: str = "", max_history: int = 100):
        self.id = str(uuid4())[:8]
        self.system_prompt = system_prompt
        self.max_history = max_history
        self.entries: list[ConversationEntry] = []
        self.created_at = datetime.now().isoformat()
        self.title = "New conversation"
        self._lock = threading.Lock()

    def add_message(self, msg: Message) -> ConversationEntry:
        """Add a Message object to history."""
        entry = ConversationEntry(
            id=str(uuid4())[:8],
            role=msg.role,
            content=msg.content,
            timestamp=datetime.now().isoformat(),
            tool_calls=msg.tool_calls,
            tool_call_id=msg.tool_call_id,
            files=msg.files,
        )
        with self._lock:
            self.entries.append(entry)
            self._trim()
        return entry

    def add(self, role: str, content: str, **kwargs: Any) -> ConversationEntry:
        """Add a simple message to history."""
        entry = ConversationEntry(
            id=str(uuid4())[:8],
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            **kwargs,
        )
        with self._lock:
            self.entries.append(entry)
            self._trim()
        return entry

    def _trim(self) -> None:
        """Trim history to max_history entries, preserving tool pairs."""
        if len(self.entries) <= self.max_history:
            return
        # Keep removing from start while preserving tool message pairs
        while len(self.entries) > self.max_history:
            removed = self.entries.pop(0)
            # If we removed a tool call, also remove the corresponding result
            if removed.tool_calls:
                self.entries = [
                    e
                    for e in self.entries
                    if not (
                        e.role == "tool"
                        and e.tool_call_id in [tc.get("id") for tc in removed.tool_calls]
                    )
                ]

    def to_messages(self) -> list[Message]:
        """Convert history to list of Message objects for the provider."""
        with self._lock:
            entries = list(self.entries)
        messages = []
        if self.system_prompt:
            messages.append(Message(role="system", content=self.system_prompt))
        for entry in entries:
            messages.append(
                Message(
                    role=entry.role,
                    content=entry.content,
                    tool_calls=entry.tool_calls,
                    tool_call_id=entry.tool_call_id,
                    files=entry.files,
                )
            )
        return messages

    def to_dict(self) -> dict[str, Any]:
        """Serialize conversation to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "system_prompt": self.system_prompt,
            "created_at": self.created_at,
            "entries": [asdict(e) for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Conversation:
        """Deserialize conversation from dictionary."""
        conv = cls(
            system_prompt=data.get("system_prompt", ""),
            max_history=100,
        )
        conv.id = data.get("id", conv.id)
        conv.title = data.get("title", "Restored conversation")
        conv.created_at = data.get("created_at", conv.created_at)
        with conv._lock:
            for entry_data in data.get("entries", []):
                conv.entries.append(ConversationEntry(**entry_data))
        return conv

    def save(self, path: Path) -> None:
        """Save conversation to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> Conversation:
        """Load conversation from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)

    def clear(self) -> None:
        """Clear all entries but keep system prompt."""
        with self._lock:
            self.entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self.entries)

    def last_message(self) -> ConversationEntry | None:
        """Get the last message in the conversation."""
        with self._lock:
            return self.entries[-1] if self.entries else None
