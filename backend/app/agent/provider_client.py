from __future__ import annotations

from collections.abc import AsyncGenerator

import litellm
from litellm import acompletion
from loguru import logger


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

    async def stream_chat(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        try:
            response = await acompletion(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                api_key=self.api_key,
                api_base=self.api_base,
                stream=True,
            )

            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as exc:
            logger.exception("Provider stream failed")
            yield f"[provider_error] {exc}"
