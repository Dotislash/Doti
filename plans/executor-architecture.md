# DOTI Executor Architecture Plan

> Version: v1.0 | Date: 2026-03-09

## Overview

Executor = MCP Server running inside Docker container, providing workspace tools (shell, filesystem).
Gateway connects to it via Streamable HTTP (MCP protocol), same as any other MCP server.

## Architecture

```
Gateway (host) ──MCP protocol──► Executor (Docker container)
                                  ├── shell_exec (RTK)
                                  ├── read_file (RTK)
                                  ├── write_file
                                  ├── list_dir (RTK)
                                  └── (future: doc parser)
```

## Container Lifecycle: running → stopped (preserved) → removed
- stopped: env preserved (pip installs, compiled artifacts)
- docker start: second-level recovery

## Thread Binding
- Thread can optionally bind an executor
- Multiple threads can share one executor
- Main: default no executor, user can force-attach
- No executor = no shell/file tools (MCP-only)

## Config: independent section like MCP servers

## Implementation Phases

### Phase 1: Executor MCP Server (new `executor/` sub-project)
- Files: executor/pyproject.toml, executor/Dockerfile, executor/executor/server.py, executor/executor/tools/
- MCP server with Streamable HTTP transport on :8811
- Tools: shell_exec (RTK), read_file, write_file, list_dir, find_files

### Phase 2: ExecutorManager (gateway side)
- Files: backend/app/executor/manager.py, backend/app/executor/client.py
- Docker container create/start/stop/remove
- MCP client connection
- Idle timeout detection

### Phase 3: Thread Binding + Protocol
- Thread model: add executor field
- Agent runtime: inject executor tools per thread
- WS protocol: executor messages

### Phase 4: Frontend UX
- Chat toolbar: model switcher, MCP toggle, thinking mode
- Slash command system
- Executor status display
