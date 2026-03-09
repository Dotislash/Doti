# Phase 3: Tool System

## Goal
Enable the agent to use tools (shell, filesystem) with risk-level-based approval.

## Sub-tasks

### 3.1 — Tool base class + Registry
**Files:** `backend/app/tools/base.py`, `backend/app/tools/registry.py`
- BaseTool ABC: name, description, parameters (JSON Schema), risk_level, async execute()
- RiskLevel enum: low, medium, high, critical
- ToolRegistry: register, get, list, dispatch tool calls

### 3.2 — Built-in tools: filesystem
**Files:** `backend/app/tools/builtins/filesystem.py`
- read_file (low): read file content
- write_file (medium): write/overwrite file
- list_directory (low): list directory contents

### 3.3 — Built-in tools: shell
**Files:** `backend/app/tools/builtins/shell.py`
- shell_exec (high): execute shell command, return stdout/stderr
- Timeout + output limit for safety

### 3.4 — Agent loop with tool calls
**Files:** `backend/app/agent/runtime.py`
- After LLM response, check for tool_calls in response
- Execute tool calls via registry
- Feed results back to LLM for next iteration
- Max iterations (prevent infinite loops)

### 3.5 — WS protocol: tool events
**Files:** `backend/app/api/ws/protocol.py`, `backend/app/api/ws/router.py`
- tool.request: approval request for high/critical tools
- tool.result: tool execution result
- tool.approve: client approves/denies tool call

### 3.6 — Frontend: tool call rendering + approval UI
**Files:** frontend components + store
- Show tool calls in message stream
- Approval dialog for high/critical tools
- Tool result display (collapsible)

## Test gates
- [ ] Tool registry registers and dispatches tools
- [ ] Filesystem tools read/write/list correctly
- [ ] Shell tool executes with timeout
- [ ] Agent loop handles tool calls and feeds results back
- [ ] High-risk tools pause for approval
