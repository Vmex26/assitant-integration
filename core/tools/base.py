"""
Base classes for the tool system.

Tools are capabilities the AI can invoke during a conversation,
such as reading files, executing commands, or searching the web.
"""

from abc import ABC, abstractmethod
from typing import Any

from core.providers.base import ToolDefinition


class BaseTool(ABC):
    """Abstract base for all tools the AI can use."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this tool does."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema for the tool's parameters."""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """Execute the tool with given arguments and return result string."""
        ...

    def to_definition(self) -> ToolDefinition:
        """Convert to a ToolDefinition for provider consumption."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )


class ToolRegistry:
    """Registry of all available tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool by its name."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_all(self) -> list[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_definitions(self) -> list[ToolDefinition]:
        """Get ToolDefinitions for all registered tools."""
        return [t.to_definition() for t in self._tools.values()]

    async def execute(self, name: str, **kwargs: Any) -> str:
        """Execute a tool by name with given arguments."""
        tool = self.get(name)
        if not tool:
            return f"Error: Unknown tool '{name}'. Available: {list(self._tools.keys())}"
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return f"Error executing '{name}': {e}"
