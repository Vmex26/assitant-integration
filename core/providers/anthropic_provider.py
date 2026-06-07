"""
Anthropic Claude provider implementation.

Supports Claude models with tool/function calling and image inputs.
"""

import base64
import io
import json
import mimetypes
from typing import Any, Callable, Dict, List, Optional

from anthropic import AsyncAnthropic

from PIL import Image

from .base import BaseProvider, Message, ProviderResult, ToolDefinition


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic Claude models."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        api_key = config.get("api_key", "")
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = config.get("model", "claude-sonnet-4-20250514")
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
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        on_stream: Optional[Callable[[str], None]] = None,
    ) -> ProviderResult:
        system_text = ""
        api_messages = []

        for msg in messages:
            if msg.role == "system":
                system_text += msg.content + "\n"
                continue

            if msg.role == "tool":
                api_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content,
                        }
                    ],
                })
            elif msg.role == "assistant" and msg.tool_calls:
                blocks = []
                if msg.content:
                    blocks.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    try:
                        parsed_input = json.loads(tc["function"]["arguments"])
                    except (json.JSONDecodeError, KeyError):
                        parsed_input = {}
                    blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": parsed_input,
                    })
                api_messages.append({"role": "assistant", "content": blocks})
            elif msg.role == "user" and msg.files:
                blocks = [{"type": "text", "text": msg.content}]
                for file_path in msg.files:
                    media_block = self._encode_media(file_path)
                    if media_block:
                        blocks.append(media_block)
                api_messages.append({"role": "user", "content": blocks})
            else:
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if system_text.strip():
            kwargs["system"] = system_text.strip()

        formatted_tools = None
        if tools:
            formatted_tools = self.format_tools(tools)
            kwargs["tools"] = formatted_tools

        if on_stream and self.supports_streaming():
            return await self._stream_chat(kwargs, on_stream)

        response = await self.client.messages.create(**kwargs)

        tool_calls = None
        content_text = ""
        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                if tool_calls is None:
                    tool_calls = []
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    },
                })

        return ProviderResult(
            content=content_text,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "stop",
            usage={
                "prompt_tokens": response.usage.input_tokens if response.usage else 0,
                "completion_tokens": response.usage.output_tokens if response.usage else 0,
            },
        )

    async def _stream_chat(
        self,
        kwargs: Dict[str, Any],
        on_stream: Callable[[str], None],
    ) -> ProviderResult:
        """Handle streaming response from Anthropic."""
        full_content = ""
        tool_calls: List[Dict[str, Any]] = []

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                full_content += text
                on_stream(text)

            response = await stream.get_final_message()

            for block in response.content:
                if block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input),
                        },
                    })

        return ProviderResult(
            content=full_content,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=response.stop_reason or "stop",
        )

    def _encode_media(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Encode a file for multimodal input."""

        file_ext = file_path.lower().rsplit(".", 1)[-1] if "." in file_path else ""
        image_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
        doc_extensions = {"pdf", "txt", "py", "js", "ts", "html", "css", "json", "md"}

        if file_ext in image_extensions:
            try:
                img = Image.open(file_path)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.thumbnail((2048, 2048), Image.LANCZOS)
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                media_type = "image/jpeg"
                if file_ext == "png":
                    media_type = "image/png"
                elif file_ext == "gif":
                    media_type = "image/gif"
                elif file_ext == "webp":
                    media_type = "image/webp"
                return {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64.b64encode(buffer.getvalue()).decode("utf-8"),
                    },
                }
            except Exception:
                return None
        elif file_ext in doc_extensions or file_ext == "pdf":
            try:
                with open(file_path, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                mime_type, _ = mimetypes.guess_type(file_path)
                return {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type or "text/plain",
                        "data": data,
                    },
                }
            except Exception:
                return None
        return None

    def format_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]
