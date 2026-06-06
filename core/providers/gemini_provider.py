"""
Google Gemini provider implementation.

Supports Gemini 2.0 Flash, Gemini 2.5 Flash, and other Gemini models
with tool/function calling and image inputs.
"""

import base64
import json
from typing import Any, Callable, Dict, List, Optional

from .base import BaseProvider, Message, ProviderResult, ToolDefinition


class GeminiProvider(BaseProvider):
    """Provider for Google Gemini models via the google-genai SDK."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "gemini-2.0-flash")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 4096)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key) if self.api_key else None
        return self._client

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
        if not self.api_key:
            return ProviderResult(
                content="Error: Gemini API key not configured. Set it in Settings > Providers.",
                finish_reason="error",
            )
        if self.client is None:
            return ProviderResult(
                content="Error: Failed to initialize Gemini client. Check your API key.",
                finish_reason="error",
            )

        from google.genai import types as genai_types

        system_instruction = None
        contents = []
        pending_user_parts = []

        def flush_user_parts():
            """Merge accumulated user parts into a single user turn."""
            if pending_user_parts:
                contents.append(genai_types.Content(role="user", parts=list(pending_user_parts)))
                pending_user_parts.clear()

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
                continue

            if msg.role == "user":
                parts = []
                if msg.content:
                    parts.append(genai_types.Part.from_text(text=msg.content))
                for file_path in msg.files:
                    media_part = self._encode_media(file_path)
                    if media_part:
                        parts.append(media_part)
                # Accumulate user parts — may merge with a function_response from a tool
                pending_user_parts.extend(parts)

            elif msg.role == "assistant":
                flush_user_parts()
                parts = []
                if msg.content:
                    parts.append(genai_types.Part.from_text(text=msg.content))
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        try:
                            args = json.loads(tc["function"]["arguments"])
                        except (json.JSONDecodeError, KeyError):
                            args = {}
                        part = genai_types.Part.from_function_call(
                            name=tc["function"]["name"],
                            args=args,
                        )
                        sig = tc.get("thought_signature")
                        if sig:
                            part.thought_signature = base64.b64decode(sig)
                        parts.append(part)
                if parts:
                    contents.append(genai_types.Content(role="model", parts=parts))

            elif msg.role == "tool":
                pending_user_parts.append(
                    genai_types.Part.from_function_response(
                        name=msg.name or "unknown",
                        response={"result": msg.content},
                    )
                )

        flush_user_parts()

        genai_tools = None
        if tools:
            genai_tools = self.format_tools(tools)

        config_kwargs: Dict[str, Any] = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens,
        }
        if genai_tools:
            config_kwargs["tools"] = genai_tools

        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        generate_config = genai_types.GenerateContentConfig(**config_kwargs)

        if on_stream:
            return await self._stream_chat(contents, generate_config, on_stream)

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=generate_config,
            )
        except Exception as e:
            return ProviderResult(
                content=f"Error: Gemini API request failed: {e}",
                finish_reason="error",
            )

        tool_calls = None
        content_text = ""

        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.text:
                        content_text += part.text
                    elif part.function_call:
                        if tool_calls is None:
                            tool_calls = []
                        sig = part.thought_signature
                        tool_calls.append({
                            "id": part.function_call.id,
                            "type": "function",
                            "function": {
                                "name": part.function_call.name,
                                "arguments": json.dumps(part.function_call.args),
                            },
                            "thought_signature": base64.b64encode(sig).decode() if sig else None,
                        })
            finish = candidate.finish_reason or ""
            if finish == "STOP" or finish == 1:
                finish_reason = "stop"
            elif finish == "MAX_TOKENS" or finish == 4:
                finish_reason = "length"
            else:
                finish_reason = str(finish)
        else:
            finish_reason = "error"
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                content_text = f"Error: Content blocked - {response.prompt_feedback.block_reason}"

        return ProviderResult(
            content=content_text,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )

    async def _stream_chat(
        self,
        contents: List[Any],
        generate_config: Any,
        on_stream: Callable[[str], None],
    ) -> ProviderResult:
        """Handle streaming response from Gemini."""
        from google.genai import types as genai_types

        full_content = ""
        tool_calls = None
        finish_reason = "stop"

        try:
            stream = await self.client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=generate_config,
            )
            async for chunk in stream:
                if chunk.candidates:
                    candidate = chunk.candidates[0]
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.text:
                                full_content += part.text
                                on_stream(part.text)
                            elif part.function_call:
                                if tool_calls is None:
                                    tool_calls = []
                                sig = part.thought_signature
                                tool_calls.append({
                                    "id": part.function_call.name,
                                    "type": "function",
                                    "function": {
                                        "name": part.function_call.name,
                                        "arguments": json.dumps(part.function_call.args),
                                    },
                                    "thought_signature": base64.b64encode(sig).decode() if sig else None,
                                })
                    if candidate.finish_reason:
                        fr = candidate.finish_reason
                        if fr == 1:
                            finish_reason = "stop"
                        elif fr == 4:
                            finish_reason = "length"
                        else:
                            finish_reason = str(fr)
        except Exception as e:
            return ProviderResult(
                content=f"Error during streaming: {e}",
                finish_reason="error",
            )

        return ProviderResult(
            content=full_content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )

    def _encode_media(self, file_path: str) -> Any:
        """Encode a file for multimodal input to Gemini."""
        import base64
        import mimetypes

        from google.genai import types as genai_types

        ext = file_path.lower().rsplit(".", 1)[-1] if "." in file_path else ""
        image_exts = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}

        try:
            if ext in image_exts:
                from PIL import Image
                import io
                img = Image.open(file_path)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.thumbnail((2048, 2048), Image.LANCZOS)
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                mime_type = "image/jpeg"
                return genai_types.Part.from_bytes(
                    data=buffer.getvalue(),
                    mime_type=mime_type,
                )
            else:
                mime_type, _ = mimetypes.guess_type(file_path)
                with open(file_path, "rb") as f:
                    data = f.read()
                return genai_types.Part.from_bytes(
                    data=data,
                    mime_type=mime_type or "text/plain",
                )
        except Exception:
            return None

    def format_tools(self, tools: List[ToolDefinition]) -> List[Any]:
        """Convert internal tool definitions to Gemini function declarations."""
        from google.genai import types as genai_types

        function_declarations = []
        for t in tools:
            function_declarations.append(
                genai_types.FunctionDeclaration(
                    name=t.name,
                    description=t.description,
                    parameters=t.parameters,
                )
            )
        return [genai_types.Tool(function_declarations=function_declarations)]
