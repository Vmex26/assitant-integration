from pathlib import Path

from core.conversation import Conversation
from core.storage import ConversationStorage


def test_save_and_load_conversation(tmp_db_path: Path):
    storage = ConversationStorage(db_path=tmp_db_path)
    conv = Conversation(system_prompt="Hello")
    conv.add("user", "Hi")
    conv.add("assistant", "Hey there!")

    storage.save_conversation(conv)
    loaded = storage.load_conversation(conv.id)

    assert loaded is not None
    assert loaded.id == conv.id
    assert loaded.system_prompt == conv.system_prompt
    assert len(loaded) == 2
    assert loaded.entries[0].content == "Hi"
    assert loaded.entries[1].content == "Hey there!"


def test_load_nonexistent_returns_none(tmp_db_path: Path):
    storage = ConversationStorage(db_path=tmp_db_path)
    assert storage.load_conversation("nonexistent") is None


def test_list_conversations(tmp_db_path: Path):
    storage = ConversationStorage(db_path=tmp_db_path)
    conv1 = Conversation()
    conv2 = Conversation()
    conv1.add("user", "A")
    conv2.add("user", "B")
    storage.save_conversation(conv1)
    storage.save_conversation(conv2)

    convs = storage.list_conversations()
    assert len(convs) == 2


def test_list_empty(tmp_db_path: Path):
    storage = ConversationStorage(db_path=tmp_db_path)
    assert storage.list_conversations() == []


def test_delete_conversation(tmp_db_path: Path):
    storage = ConversationStorage(db_path=tmp_db_path)
    conv = Conversation()
    conv.add("user", "Hello")
    storage.save_conversation(conv)
    assert len(storage.list_conversations()) == 1

    storage.delete_conversation(conv.id)
    assert len(storage.list_conversations()) == 0
    assert storage.load_conversation(conv.id) is None


def test_update_title(tmp_db_path: Path):
    storage = ConversationStorage(db_path=tmp_db_path)
    conv = Conversation()
    conv.add("user", "Test")
    storage.save_conversation(conv)

    storage.update_title(conv.id, "New Title")
    loaded = storage.load_conversation(conv.id)
    assert loaded is not None
    assert loaded.title == "New Title"


def test_save_empty_conversation(tmp_db_path: Path):
    storage = ConversationStorage(db_path=tmp_db_path)
    conv = Conversation()
    storage.save_conversation(conv)

    loaded = storage.load_conversation(conv.id)
    assert loaded is not None
    assert len(loaded) == 0


def test_conversation_with_tool_calls(tmp_db_path: Path):
    storage = ConversationStorage(db_path=tmp_db_path)
    conv = Conversation()
    conv.add(
        "assistant",
        "",
        tool_calls=[
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "test", "arguments": "{}"},
            }
        ],
    )
    conv.add("tool", "result", tool_call_id="call_1")
    storage.save_conversation(conv)

    loaded = storage.load_conversation(conv.id)
    assert loaded is not None
    assert loaded.entries[0].tool_calls is not None
    assert loaded.entries[0].tool_calls[0]["id"] == "call_1"
    assert loaded.entries[1].tool_call_id == "call_1"
