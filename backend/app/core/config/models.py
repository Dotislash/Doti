from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ThinkingMode(str, Enum):
    none = "none"
    mandatory = "mandatory"
    budget = "budget"


class ThinkingStyle(str, Enum):
    budget = "budget"
    level_openai = "level_openai"


class ThinkingConfig(BaseModel):
    mode: ThinkingMode = ThinkingMode.none
    style: ThinkingStyle | None = None
    default_budget: int | None = None
    default_level: str | None = None


class PricingConfig(BaseModel):
    input: float | None = None
    output: float | None = None


class ModelConfig(BaseModel):
    id: str
    context_window: int | None = None
    pricing: PricingConfig | None = None
    thinking: ThinkingConfig = Field(default_factory=ThinkingConfig)


class ProviderConfig(BaseModel):
    api_base: str | None = None
    api_key: str | None = None
    models: dict[str, ModelConfig] = Field(default_factory=dict)


class RoleThinkingConfig(BaseModel):
    enabled: bool = False
    budget: int | None = None
    level_openai: str | None = None


class ContextConfig(BaseModel):
    max_tokens: int = 200000
    compression_threshold: float = 0.6


class ProfileRoleConfig(BaseModel):
    model: str
    thinking: RoleThinkingConfig = Field(default_factory=RoleThinkingConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)


class ProfileConfig(BaseModel):
    name: str = "default"
    description: str = ""
    primary: ProfileRoleConfig | None = None
    long_context: ProfileRoleConfig | None = None
    automation: ProfileRoleConfig | None = None


class ToolApprovalPolicy(str, Enum):
    ask_first = "ask_first"
    auto = "auto"
    auto_with_allowlist = "auto_with_allowlist"


class SecurityConfig(BaseModel):
    tool_approval: ToolApprovalPolicy = ToolApprovalPolicy.ask_first
    tool_allowlist: list[str] = Field(default_factory=list)
    sandbox_runtime: str = "subprocess"


class ConcurrencyConfig(BaseModel):
    max_parallel_sessions: int = 5
    resource_acquire_timeout: int = 60


class ExecutorConfig(BaseModel):
    id: str
    workspace: str
    image: str = "doti-sandbox:latest"
    idle_timeout: int = 600
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    network: bool = False
    rtk_enabled: bool = True


class DotiConfig(BaseModel):
    """Root configuration for the doti platform."""

    config_version: int = 3
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    profile: ProfileConfig = Field(default_factory=ProfileConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    executors: dict[str, ExecutorConfig] = Field(default_factory=dict)
    workspace: str = "."

    def resolve_model(self, model_ref: str) -> tuple[ProviderConfig, ModelConfig] | None:
        """Resolve 'provider/model' reference to (provider, model) configs."""
        parts = model_ref.split("/", 1)
        if len(parts) != 2:
            return None
        provider_alias, model_alias = parts
        provider = self.providers.get(provider_alias)
        if provider is None:
            return None
        model = provider.models.get(model_alias)
        if model is None:
            return None
        return (provider, model)

    def list_all_models(self) -> list[dict[str, str]]:
        """Return list of all registered models with their refs."""
        result = []
        for provider_alias, provider in self.providers.items():
            for model_alias, model in provider.models.items():
                result.append(
                    {
                        "ref": f"{provider_alias}/{model_alias}",
                        "id": model.id,
                        "provider": provider_alias,
                        "alias": model_alias,
                        "thinking_mode": model.thinking.mode.value,
                    }
                )
        return result
