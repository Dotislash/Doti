"""Main MCP server entry point for doti-executor."""

from __future__ import annotations

import argparse
import importlib
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator

from mcp.server.fastmcp import FastMCP


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8811
DEFAULT_WORKSPACE = "/workspace"


@dataclass(slots=True)
class AppContext:
    workspace: Path
    host: str
    port: int


def _register_tool_modules(mcp: FastMCP, workspace: str) -> None:
    """Import tool modules and register tools."""
    for module_name in ("executor.tools.shell", "executor.tools.filesystem"):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            logging.warning("Tool module %s not found, skipping", module_name)
            continue

        register = getattr(module, "register", None)
        if callable(register):
            register(mcp, workspace)


def create_server(host: str, port: int, workspace: str) -> FastMCP:
    workspace_path = Path(workspace)

    @asynccontextmanager
    async def lifespan(_: Any) -> AsyncIterator[AppContext]:
        if not workspace_path.is_dir():
            raise FileNotFoundError(f"Workspace directory not found: {workspace_path}")

        logging.info(
            "Starting doti-executor MCP server (workspace=%s, host=%s, port=%s)",
            workspace_path,
            host,
            port,
        )
        yield AppContext(workspace=workspace_path, host=host, port=port)

    mcp = FastMCP("doti-executor", host=host, port=port, lifespan=lifespan)
    _register_tool_modules(mcp, workspace)
    return mcp


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the doti-executor MCP server")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to bind (default: {DEFAULT_HOST})")
    parser.add_argument(
        "--port",
        default=DEFAULT_PORT,
        type=int,
        help=f"Port to bind (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--workspace",
        default=DEFAULT_WORKSPACE,
        help=f"Workspace mount path (default: {DEFAULT_WORKSPACE})",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args()
    server = create_server(host=args.host, port=args.port, workspace=args.workspace)
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
