"""
Abstract base class for AI model providers.

Defines the interface that all providers must implement,
including support for tool/function calling and multimodal inputs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolDefinition:
    """Describes a tool/function available to the AI model."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for parameters


@dataclass
class Message:
    """Represents a single message in a conversation."""
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    files: List[str] = field(default_factory=list)  # File paths attached


@dataclass
class ProviderResult:
    """Result from a provider model call."""
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: str = "stop"
    usage: Optional[Dict[str, int]] = None


class BaseProvider(ABC):
    """Abstract interface for AI model providers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        on_stream: Optional[Callable[[str], None]] = None,
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

    def format_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
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
