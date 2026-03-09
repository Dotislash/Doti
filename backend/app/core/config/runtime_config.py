from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOTI_")

    model: str = "anthropic/claude-sonnet-4-5"
    api_key: str | None = None
    api_base: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    workspace: str = "."
    host: str = "0.0.0.0"
    port: int = 8000
