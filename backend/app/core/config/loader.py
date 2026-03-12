from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config.models import (
    DotiConfig,
    ModelConfig,
    ProfileConfig,
    ProfileRoleConfig,
    ProviderConfig,
)
from app.core.config.runtime_config import RuntimeConfig


def load_config(config_path: str | Path | None = None, workspace: str = ".") -> DotiConfig:
    yaml_path: Path | None = None

    if config_path is not None:
        candidate = Path(config_path)
        if candidate.exists() and candidate.is_file():
            yaml_path = candidate

    if yaml_path is None:
        default_path = Path(workspace) / "config.yaml"
        if default_path.exists() and default_path.is_file():
            yaml_path = default_path

    if yaml_path is None:
        config = _from_env()
        if config.workspace == "." and workspace != ".":
            config.workspace = workspace
        return config

    data = _load_yaml(yaml_path)
    config = DotiConfig.model_validate(data)
    if config.workspace == "." and workspace != ".":
        config.workspace = workspace
    return config


def _from_env() -> DotiConfig:
    model = (os.environ.get("DOTI_MODEL") or RuntimeConfig().model).strip()
    api_key = os.environ.get("DOTI_API_KEY")
    api_base = os.environ.get("DOTI_API_BASE")
    workspace = os.environ.get("DOTI_WORKSPACE", ".")

    provider = ProviderConfig(
        api_base=api_base,
        api_key=api_key,
        models={"default": ModelConfig(id=model)},
    )
    profile = ProfileConfig(primary=ProfileRoleConfig(model="default/default"))

    return DotiConfig(
        providers={"default": provider},
        profile=profile,
        workspace=workspace,
    )


def _interpolate_env(data: Any) -> Any:
    def _replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        var_value = os.environ.get(var_name)
        if var_value is None:
            logger.warning("Missing environment variable for interpolation: {}", var_name)
            return ""
        return var_value

    if isinstance(data, dict):
        return {k: _interpolate_env(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_interpolate_env(item) for item in data]
    if isinstance(data, str):
        return re.sub(r"\$\{(\w+)\}", _replace, data)
    return data


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML is not installed; cannot load {}", path)
        return {}

    try:
        content = path.read_text(encoding="utf-8")
        raw = yaml.safe_load(content)
    except Exception as exc:
        logger.warning("Failed to parse YAML from {}: {}", path, exc)
        return {}

    if raw is None:
        return {}
    if not isinstance(raw, dict):
        logger.warning("YAML config root must be a mapping in {}", path)
        return {}
    return _interpolate_env(raw)


def to_runtime_config(config: DotiConfig) -> RuntimeConfig:
    primary_ref = config.profile.primary.model if config.profile.primary is not None else ""
    resolved = config.resolve_model(primary_ref) if primary_ref else None

    if resolved is None:
        logger.warning("Unable to resolve primary model reference: {}", primary_ref)
        return RuntimeConfig(
            temperature=0.7,
            max_tokens=4096,
            workspace=config.workspace,
        )

    provider, model = resolved
    max_tokens = 4096
    if config.profile.primary is not None:
        max_tokens = config.profile.primary.context.max_tokens

    return RuntimeConfig(
        model=model.id,
        api_key=provider.api_key,
        api_base=provider.api_base,
        temperature=0.7,
        max_tokens=max_tokens,
        workspace=config.workspace,
    )
