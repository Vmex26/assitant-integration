"""
OpenAI provider implementation.

Supports GPT-4o, GPT-4-turbo, and other OpenAI models
with tool/function calling and image inputs.
"""

from typing import Any, Callable, Dict, List, Optional

from openai import AsyncOpenAI

from .base import BaseProvider, Message, ProviderResult, ToolDefinition


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI API-compatible models."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        api_key = config.get("api_key", "")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = config.get("model", "gpt-4o")
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
        openai_messages = []
        for msg in messages:
            if msg.role == "tool":
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content,
                })
            elif msg.role == "assistant" and msg.tool_calls:
                openai_messages.append({
                    "role": "assistant",
                    "content": msg.content or None,
                    "tool_calls": [
                        {
                            "id": tc.get("id"),
                            "type": "function",
                            "function": {
                                "name": tc["function"]["name"],
                                "arguments": tc["function"]["arguments"],
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
            elif msg.role == "user" and msg.files:
                content: List[Dict[str, Any]] = [{"type": "text", "text": msg.content}]
                for file_path in msg.files:
                    image_data = self._encode_image(file_path)
                    if image_data:
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                        })
                openai_messages.append({"role": "user", "content": content})
            else:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        formatted_tools = None
        if tools:
            formatted_tools = self.format_tools(tools)
            kwargs["tools"] = formatted_tools
            kwargs["tool_choice"] = "auto"

        if on_stream and self.supports_streaming():
            return await self._stream_chat(kwargs, on_stream)

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        tool_calls = None
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ]

        return ProviderResult(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )

    async def _stream_chat(
        self,
        kwargs: Dict[str, Any],
        on_stream: Callable[[str], None],
    ) -> ProviderResult:
        """Handle streaming response from OpenAI."""
        stream = await self.client.chat.completions.create(**kwargs, stream=True)
        full_content = ""
        tool_calls_map: Dict[int, Dict[str, Any]] = {}

        finish_reason = "stop"
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            if chunk.choices:
                finish_reason = chunk.choices[0].finish_reason or finish_reason

            if delta.content:
                full_content += delta.content
                on_stream(delta.content)

            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_map:
                        tool_calls_map[idx] = {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    if tc_delta.id:
                        tool_calls_map[idx]["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            tool_calls_map[idx]["function"]["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            tool_calls_map[idx]["function"]["arguments"] += tc_delta.function.arguments
        tool_calls = list(tool_calls_map.values()) if tool_calls_map else None

        return ProviderResult(
            content=full_content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )

    @staticmethod
    def _encode_image(file_path: str) -> Optional[str]:
        """Encode an image file to base64 for multimodal input."""
        import base64
        try:
            from PIL import Image
            img = Image.open(file_path)
            # Convert to RGB if necessary and resize to reasonable dimensions
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((2048, 2048), Image.LANCZOS)

            import io
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception:
            return None

    def format_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
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
