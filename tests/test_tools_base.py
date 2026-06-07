import pytest

from core.tools.base import BaseTool, ToolRegistry


class DummyTool(BaseTool):
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def description(self) -> str:
        return "A dummy tool for testing"

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> str:
        return f"executed with {kwargs}"


@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.register(DummyTool())
    return reg


def test_register_and_get(registry: ToolRegistry):
    tool = registry.get("dummy")
    assert tool is not None
    assert tool.name == "dummy"


def test_get_nonexistent(registry: ToolRegistry):
    assert registry.get("nonexistent") is None


def test_unregister(registry: ToolRegistry):
    registry.unregister("dummy")
    assert registry.get("dummy") is None


def test_get_all(registry: ToolRegistry):
    tools = registry.get_all()
    assert len(tools) == 1
    assert tools[0].name == "dummy"


def test_get_definitions(registry: ToolRegistry):
    defs = registry.get_definitions()
    assert len(defs) == 1
    assert defs[0].name == "dummy"


def test_to_definition():
    tool = DummyTool()
    td = tool.to_definition()
    assert td.name == "dummy"
    assert td.description == "A dummy tool for testing"


@pytest.mark.asyncio
async def test_execute(registry: ToolRegistry):
    result = await registry.execute("dummy", key="value")
    assert result == "executed with {'key': 'value'}"


@pytest.mark.asyncio
async def test_execute_unknown(registry: ToolRegistry):
    result = await registry.execute("ghost")
    assert "Error: Unknown tool" in result
    assert "ghost" in result


@pytest.mark.asyncio
async def test_execute_error(registry: ToolRegistry):
    class BrokenTool(BaseTool):
        name = "broken"
        description = "Broken tool"
        parameters = {}

        async def execute(self, **kwargs) -> str:
            raise ValueError("something broke")

    registry.register(BrokenTool())
    result = await registry.execute("broken")
    assert "Error executing" in result
