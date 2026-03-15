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
    model = (os.environ.get("DOTI_MODEL") or "anthropic/claude-sonnet-4-5").strip()
    if not model:
        model = "anthropic/claude-sonnet-4-5"
    api_key = os.environ.get("DOTI_API_KEY")
    api_base = os.environ.get("DOTI_API_BASE")
    workspace = os.environ.get("DOTI_WORKSPACE", ".")
    host = os.environ.get("DOTI_HOST", "127.0.0.1")
    port = _parse_env_int("DOTI_PORT", 8000)
    api_token = os.environ.get("DOTI_API_TOKEN")

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
        host=host,
        port=port,
        api_token=api_token,
    )


def _parse_env_int(var_name: str, default: int) -> int:
    raw = os.environ.get(var_name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid integer for {}: {}", var_name, raw)
        return default


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


def _remove_matching_values(value: Any, defaults: Any) -> Any:
    if isinstance(value, dict) and isinstance(defaults, dict):
        trimmed: dict[str, Any] = {}
        for key, item in value.items():
            if key in defaults:
                reduced = _remove_matching_values(item, defaults[key])
                if reduced is not None:
                    trimmed[key] = reduced
            else:
                trimmed[key] = item
        return trimmed or None

    if isinstance(value, list) and isinstance(defaults, list) and value == defaults:
        return None

    if value == defaults:
        return None

    return value


def _env_backed_values() -> dict[str, Any]:
    env_defaults: dict[str, Any] = {}

    if "DOTI_WORKSPACE" in os.environ:
        env_defaults["workspace"] = os.environ["DOTI_WORKSPACE"]
    if "DOTI_HOST" in os.environ:
        env_defaults["host"] = os.environ["DOTI_HOST"]
    if "DOTI_PORT" in os.environ:
        try:
            env_defaults["port"] = int(os.environ["DOTI_PORT"])
        except ValueError:
            logger.warning("Invalid integer for DOTI_PORT: {}", os.environ["DOTI_PORT"])
    if "DOTI_API_TOKEN" in os.environ:
        env_defaults["api_token"] = os.environ["DOTI_API_TOKEN"]

    provider_defaults: dict[str, Any] = {}
    model = os.environ.get("DOTI_MODEL")
    if model is not None:
        provider_defaults.setdefault("models", {}).setdefault("default", {})["id"] = model
    api_key = os.environ.get("DOTI_API_KEY")
    if api_key is not None:
        provider_defaults["api_key"] = api_key
    api_base = os.environ.get("DOTI_API_BASE")
    if api_base is not None:
        provider_defaults["api_base"] = api_base
    if provider_defaults:
        env_defaults.setdefault("providers", {}).setdefault("default", {}).update(provider_defaults)

    return env_defaults


def save_config(config: DotiConfig, path: Path) -> None:
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML is not installed; cannot save {}", path)
        return

    data = config.model_dump(mode="json", exclude_none=True)
    env_defaults = _env_backed_values()
    reduced = _remove_matching_values(data, env_defaults) if env_defaults else data
    payload = reduced if isinstance(reduced, dict) else {}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
