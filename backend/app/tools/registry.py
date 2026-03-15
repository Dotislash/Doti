from __future__ import annotations

from typing import Any

from app.tools.base import BaseTool, ToolResult

_RETRY_HINT = "\n\n[Analyze the error and try a different approach.]"

_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _validate_params(schema: dict[str, Any], params: dict[str, Any]) -> list[str]:
    """Validate params against a JSON Schema object. Returns error messages."""
    errors: list[str] = []
    props = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in params:
            errors.append(f"missing required parameter '{key}'")
    for key, value in params.items():
        if key not in props:
            continue
        expected_type = props[key].get("type")
        if expected_type and expected_type in _TYPE_MAP:
            if not isinstance(value, _TYPE_MAP[expected_type]):
                errors.append(f"'{key}' should be {expected_type}, got {type(value).__name__}")
    return errors


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def to_openai_tools(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self.list_tools()
        ]

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Tool not found: {name}")
        errors = _validate_params(tool.parameters, arguments)
        if errors:
            detail = "; ".join(errors)
            return ToolResult(
                output=f"Invalid parameters for '{name}': {detail}{_RETRY_HINT}",
                is_error=True,
            )
        return await tool.execute(**arguments)


def create_default_registry(workspace: str = ".", executor_manager=None) -> ToolRegistry:
    """Create registry with safe, non-destructive tools only.

    Shell execution is intentionally excluded — it belongs to Executors.
    """
    from app.tools.builtins.filesystem import ListDirectoryTool, ReadFileTool, WriteFileTool

    registry = ToolRegistry()
    registry.register(ReadFileTool(workspace=workspace))
    registry.register(WriteFileTool(workspace=workspace))
    registry.register(ListDirectoryTool(workspace=workspace))
    if executor_manager is not None:
        from app.tools.builtins.executor_tool import ExecutorRunTool

        registry.register(ExecutorRunTool(executor_manager=executor_manager, workspace=workspace))
    return registry
