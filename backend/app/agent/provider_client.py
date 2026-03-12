"""LLM provider client with streaming and tool call support."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

import litellm
from litellm import acompletion
from loguru import logger


@dataclass
class ToolCallChunk:
    """Accumulated tool call from streamed response."""
    id: str
    name: str
    arguments: str  # JSON string


@dataclass
class StreamResult:
    """Result of a streamed LLM response."""
    content: str = ""
    tool_calls: list[ToolCallChunk] = field(default_factory=list)
    finish_reason: str | None = None
    error: str | None = None


class ProviderClient:
    def __init__(
        self,
        model: str,
        api_key: str | None,
        api_base: str | None,
        temperature: float,
        max_tokens: int,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.temperature = temperature
        self.max_tokens = max_tokens

        litellm.suppress_debug_info = True
        litellm.drop_params = True

    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream text content tokens. For simple chat without tool handling."""
        try:
            kwargs: dict = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "api_key": self.api_key,
                "api_base": self.api_base,
                "stream": True,
            }
            if tools:
                kwargs["tools"] = tools

            response = await acompletion(**kwargs)

            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as exc:
            logger.exception("Provider stream failed")
            yield f"[provider_error] {exc}"

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> StreamResult:
        """Stream a response, accumulating both content and tool calls."""
        result = StreamResult()

        try:
            response = await acompletion(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                api_key=self.api_key,
                api_base=self.api_base,
                tools=tools,
                stream=True,
            )

            # Accumulate tool calls by index
            tc_map: dict[int, dict] = {}

            async for chunk in response:
                choice = chunk.choices[0]
                delta = choice.delta

                if delta.content:
                    result.content += delta.content

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index if hasattr(tc, "index") else 0
                        if idx not in tc_map:
                            tc_map[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc.id:
                            tc_map[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tc_map[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tc_map[idx]["arguments"] += tc.function.arguments

                if choice.finish_reason:
                    result.finish_reason = choice.finish_reason

            result.tool_calls = [
                ToolCallChunk(id=v["id"], name=v["name"], arguments=v["arguments"])
                for v in tc_map.values()
                if v["name"]
            ]

        except Exception as exc:
            logger.exception("Provider chat_with_tools failed")
            result.error = str(exc)

        return result
