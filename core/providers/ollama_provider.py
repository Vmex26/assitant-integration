"""
Ollama provider implementation.

Supports local models served via Ollama with tool calling support.
"""

import json
from collections.abc import Callable
from typing import Any

import httpx

from .base import BaseProvider, Message, ProviderResult, ToolDefinition


class OllamaProvider(BaseProvider):
    """Provider for locally-hosted Ollama models."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434").rstrip("/")
        self.model = config.get("model", "llama3")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 4096)

    def supports_tools(self) -> bool:
        return True

    def supports_images(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        on_stream: Callable[[str], None] | None = None,
    ) -> ProviderResult:
        ollama_messages = []
        for msg in messages:
            if msg.role == "tool":
                ollama_messages.append(
                    {
                        "role": "tool",
                        "content": msg.content,
                    }
                )
            elif msg.role == "assistant" and msg.tool_calls:
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.content or "",
                }
                if msg.tool_calls:
                    calls = []
                    for tc in msg.tool_calls:
                        try:
                            args = json.loads(tc["function"]["arguments"])
                        except json.JSONDecodeError, KeyError:
                            args = {}
                        calls.append(
                            {
                                "function": {
                                    "name": tc["function"]["name"],
                                    "arguments": args,
                                },
                            }
                        )
                    if calls:
                        assistant_msg["tool_calls"] = calls
                ollama_messages.append(assistant_msg)
            elif msg.role == "user" and msg.files:
                content_parts: list[dict[str, Any]] = [{"type": "text", "text": msg.content}]
                for file_path in msg.files:
                    image_data = self._encode_image(file_path)
                    if image_data:
                        content_parts.append(
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                            }
                        )
                ollama_messages.append(
                    {
                        "role": "user",
                        "content": msg.content,
                        "images": [
                            self._encode_image(f) for f in msg.files if self._encode_image(f)
                        ],
                    }
                )
            else:
                ollama_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                    }
                )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": ollama_messages,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
            "stream": on_stream is not None,
        }

        if tools:
            payload["tools"] = self.format_tools(tools)

        async with httpx.AsyncClient(timeout=120.0) as client:
            if on_stream:
                return await self._stream_chat(client, payload, on_stream)

            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        tool_calls = None
        if "message" in data and "tool_calls" in data["message"]:
            tool_calls = []
            for tc in data["message"]["tool_calls"]:
                tool_calls.append(
                    {
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": json.dumps(tc["function"]["arguments"]),
                        },
                    }
                )

        content = data.get("message", {}).get("content", "")

        return ProviderResult(
            content=content,
            tool_calls=tool_calls,
            finish_reason=data.get("done_reason", "stop"),
        )

    async def _stream_chat(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, Any],
        on_stream: Callable[[str], None],
    ) -> ProviderResult:
        """Handle streaming response from Ollama."""
        full_content = ""
        tool_calls = None

        async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if "message" in data:
                    msg = data["message"]
                    if "content" in msg and msg["content"]:
                        full_content += msg["content"]
                        on_stream(msg["content"])
                    if "tool_calls" in msg:
                        if tool_calls is None:
                            tool_calls = []
                        for tc in msg["tool_calls"]:
                            tool_calls.append(
                                {
                                    "id": tc.get("id", ""),
                                    "type": "function",
                                    "function": {
                                        "name": tc["function"]["name"],
                                        "arguments": json.dumps(tc["function"]["arguments"]),
                                    },
                                }
                            )

        return ProviderResult(
            content=full_content,
            tool_calls=tool_calls,
            finish_reason="stop",
        )

    @staticmethod
    def _encode_image(file_path: str) -> str | None:
        """Encode an image file to base64 for multimodal input."""
        import base64

        try:
            import io

            from PIL import Image

            img = Image.open(file_path)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((2048, 2048), Image.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception:
            return None

    def format_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        return [
            {
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]
