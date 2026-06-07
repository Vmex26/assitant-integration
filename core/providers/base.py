"""
Abstract base class for AI model providers.

Defines the interface that all providers must implement,
including support for tool/function calling and multimodal inputs.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolDefinition:
    """Describes a tool/function available to the AI model."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for parameters


@dataclass
class Message:
    """Represents a single message in a conversation."""

    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None
    files: list[str] = field(default_factory=list)  # File paths attached


@dataclass
class ProviderResult:
    """Result from a provider model call."""

    content: str
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str = "stop"
    usage: dict[str, int] | None = None


class BaseProvider(ABC):
    """Abstract interface for AI model providers."""

    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        on_stream: Callable[[str], None] | None = None,
    ) -> ProviderResult:
        """Send a chat completion request to the model.

        Args:
            messages: Conversation history.
            tools: Available tool definitions for function calling.
            on_stream: Optional callback for streaming text chunks.

        Returns:
            ProviderResult with response content and optional tool calls.
        """
        ...

    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether this provider supports function/tool calling."""
        ...

    @abstractmethod
    def supports_images(self) -> bool:
        """Whether this provider supports image inputs."""
        ...

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming responses."""
        ...

    def name(self) -> str:
        """Human-readable provider name."""
        return self.__class__.__name__

    def format_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        """Convert internal tool definitions to provider-specific format.
        Override in subclass if needed. Base implementation returns raw dicts.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]
