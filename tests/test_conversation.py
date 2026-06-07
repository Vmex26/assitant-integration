from core.conversation import Conversation
from core.providers.base import Message


def test_add_message():
    conv = Conversation(system_prompt="You are a helpful assistant.")
    msg = Message(role="user", content="Hello")
    entry = conv.add_message(msg)
    assert entry.role == "user"
    assert entry.content == "Hello"
    assert len(conv) == 1


def test_add_simple():
    conv = Conversation()
    entry = conv.add("assistant", "Hi there!")
    assert entry.role == "assistant"
    assert entry.content == "Hi there!"
    assert len(conv) == 1


def test_to_messages_includes_system_prompt():
    conv = Conversation(system_prompt="You are a bot.")
    conv.add("user", "Hello")
    messages = conv.to_messages()
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"


def test_to_messages_no_system_prompt():
    conv = Conversation()
    conv.add("user", "Hello")
    messages = conv.to_messages()
    assert len(messages) == 1
    assert messages[0].role == "user"


def test_trim_respects_max_history():
    conv = Conversation(max_history=3)
    for i in range(5):
        conv.add("user", f"Message {i}")
    assert len(conv) == 3
    assert conv.entries[0].content == "Message 2"


def test_trim_preserves_tool_pairs():
    conv = Conversation(max_history=4)
    conv.add("user", "First")
    conv.add("assistant", "Tool call", tool_calls=[{"id": "call_1", "type": "function"}])
    conv.add("tool", "Result", tool_call_id="call_1")
    conv.add("user", "Second")
    conv.add("user", "Third")

    assert len(conv) == 4
    contents = [e.content for e in conv.entries]
    assert "Second" in contents
    assert "Third" in contents


def test_to_dict_roundtrip():
    conv = Conversation(system_prompt="Test prompt")
    conv.add("user", "Hello")
    conv.add("assistant", "Hi")

    data = conv.to_dict()
    restored = Conversation.from_dict(data)

    assert restored.system_prompt == conv.system_prompt
    assert len(restored) == len(conv)
    assert restored.entries[0].content == "Hello"
    assert restored.entries[1].content == "Hi"


def test_from_dict_with_tool_calls():
    data = {
        "id": "test123",
        "title": "Test",
        "system_prompt": "",
        "created_at": "2025-01-01T00:00:00",
        "entries": [
            {
                "id": "e1",
                "role": "user",
                "content": "Hello",
                "timestamp": "2025-01-01T00:00:00",
                "tool_calls": None,
                "tool_call_id": None,
                "files": [],
                "tokens": 0,
            }
        ],
    }
    conv = Conversation.from_dict(data)
    assert conv.id == "test123"
    assert conv.title == "Test"
    assert len(conv) == 1


def test_clear_keeps_system_prompt():
    conv = Conversation(system_prompt="Keep me")
    conv.add("user", "Hello")
    conv.clear()
    assert len(conv) == 0
    assert conv.system_prompt == "Keep me"


def test_last_message():
    conv = Conversation()
    assert conv.last_message() is None
    conv.add("user", "First")
    conv.add("user", "Last")
    assert conv.last_message() is not None
    assert conv.last_message().content == "Last"


def test_thread_safety():
    import threading

    conv = Conversation(max_history=100)
    errors = []

    def add_messages():
        try:
            for i in range(100):
                conv.add("user", f"msg {i}")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=add_messages) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(conv) <= 100
