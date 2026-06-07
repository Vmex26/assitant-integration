from core.providers.base import Message, ProviderResult, ToolDefinition


def test_message_defaults():
    msg = Message(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.tool_calls is None
    assert msg.tool_call_id is None
    assert msg.files == []


def test_message_with_tool_calls():
    msg = Message(
        role="assistant",
        content="",
        tool_calls=[{"id": "call_1", "type": "function"}],
        tool_call_id=None,
    )
    assert msg.tool_calls is not None
    assert msg.tool_calls[0]["id"] == "call_1"


def test_tool_definition():
    td = ToolDefinition(
        name="test_tool",
        description="A test tool",
        parameters={"type": "object", "properties": {}},
    )
    assert td.name == "test_tool"
    assert td.description == "A test tool"
    assert td.parameters["type"] == "object"


def test_provider_result_defaults():
    result = ProviderResult(content="Hello")
    assert result.content == "Hello"
    assert result.tool_calls is None
    assert result.finish_reason == "stop"
    assert result.usage is None


def test_provider_result_with_tool_calls():
    result = ProviderResult(
        content="",
        tool_calls=[{"id": "call_1"}],
        finish_reason="tool_calls",
        usage={"prompt_tokens": 10, "completion_tokens": 20},
    )
    assert result.tool_calls is not None
    assert result.finish_reason == "tool_calls"
    assert result.usage is not None
    assert result.usage["prompt_tokens"] == 10
