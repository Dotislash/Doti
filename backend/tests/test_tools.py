"""Tests for tool system — base, registry, and built-in tools."""

import pytest

from app.tools.base import RiskLevel
from app.tools.registry import ToolRegistry, create_default_registry
from app.tools.builtins.filesystem import ReadFileTool, WriteFileTool, ListDirectoryTool
from app.tools.builtins.shell import ShellExecTool


def test_default_registry_has_tools():
    registry = create_default_registry()
    tools = registry.list_tools()
    names = {t.name for t in tools}
    assert "read_file" in names
    assert "write_file" in names
    assert "list_directory" in names
    assert "shell_exec" in names


def test_registry_get():
    registry = create_default_registry()
    assert registry.get("read_file") is not None
    assert registry.get("nonexistent") is None


def test_openai_tools_format():
    registry = create_default_registry()
    tools = registry.to_openai_tools()
    assert len(tools) >= 4
    for tool in tools:
        assert tool["type"] == "function"
        assert "name" in tool["function"]
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]


def test_risk_levels():
    registry = create_default_registry()
    assert registry.get("read_file").risk_level == RiskLevel.low
    assert registry.get("list_directory").risk_level == RiskLevel.low
    assert registry.get("write_file").risk_level == RiskLevel.medium
    assert registry.get("shell_exec").risk_level == RiskLevel.high


async def test_read_file(tmp_path):
    tool = ReadFileTool(workspace=str(tmp_path))
    f = tmp_path / "test.txt"
    f.write_text("hello world", encoding="utf-8")
    result = await tool.execute(path="test.txt")
    assert result.output == "hello world"
    assert not result.is_error


async def test_read_file_not_found(tmp_path):
    tool = ReadFileTool(workspace=str(tmp_path))
    result = await tool.execute(path="nonexistent.txt")
    assert result.is_error


async def test_read_file_escape(tmp_path):
    tool = ReadFileTool(workspace=str(tmp_path))
    result = await tool.execute(path="../../etc/passwd")
    assert result.is_error
    assert "escapes workspace" in result.output


async def test_write_file(tmp_path):
    tool = WriteFileTool(workspace=str(tmp_path))
    result = await tool.execute(path="out.txt", content="test content")
    assert not result.is_error
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "test content"


async def test_list_directory(tmp_path):
    (tmp_path / "a.txt").touch()
    (tmp_path / "b_dir").mkdir()
    tool = ListDirectoryTool(workspace=str(tmp_path))
    result = await tool.execute(path=".")
    assert "[file] a.txt" in result.output
    assert "[dir] b_dir" in result.output


async def test_shell_exec(tmp_path):
    tool = ShellExecTool(workspace=str(tmp_path))
    result = await tool.execute(command="echo hello")
    assert "hello" in result.output
    assert not result.is_error


async def test_shell_exec_error(tmp_path):
    tool = ShellExecTool(workspace=str(tmp_path))
    result = await tool.execute(command="exit 1")
    assert result.is_error


async def test_registry_execute():
    registry = create_default_registry()
    result = await registry.execute("list_directory", {"path": "."})
    assert not result.is_error


async def test_registry_execute_not_found():
    registry = create_default_registry()
    with pytest.raises(KeyError):
        await registry.execute("fake_tool", {})
