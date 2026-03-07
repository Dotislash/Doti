# Spec 01: Core API Protocol

> Version: 3 | Status: Phase 1 Required | Last updated: 2026-03-07

## Overview

WebSocket primary channel for real-time interaction (streaming, approvals,
events). REST secondary channel for stateless operations (health, config,
Skill management, automation). All WebSocket messages carry a protocol version number.

## Authentication

### Client (Web UI / CLI)

v0.1 uses a shared secret token, configured in `config.yaml` under
`security.api_token`. Core refuses to start if this value is not set.
On first run, the CLI (`doti up`) auto-generates a token and writes it to
config if missing.

The token is passed as:

- **WebSocket**: Query parameter `?token=<token>` on initial connection
- **REST**: `Authorization: Bearer <token>` header

### Node Devices

Nodes authenticate with a pairing token obtained during the pairing flow:

1. User generates a 6-digit pairing code via CLI (`doti node pair`) or Web UI
2. Node agent sends the code to `POST /api/v1/nodes/pair`
3. Core returns a long-lived `auth_token` + tunnel endpoint
4. Node uses this token for all subsequent WebSocket tunnel connections

Pairing tokens can be revoked via `DELETE /api/v1/nodes/{node_id}/token`.

### Token Lifecycle

| Token Type | Lifetime | Rotation | Revocation |
|------------|----------|----------|------------|
| API token (client) | Until changed in config | Manual config change, or `doti config regen-token` | Config reload |
| Pairing code | 10 minutes | Single-use | Expires or consumed |
| Node auth token | Until revoked | Auto-rotation (Phase 3) | `DELETE .../token` or node removal |

## WebSocket Protocol

### Envelope

```json
{"v": 3, "id": "msg_01HXYZ", "type": "chat.send", "payload": {...}}
```

| Field | Type | Description |
|-------|------|-------------|
| v | int | Protocol version. Core rejects messages with unsupported versions. |
| id | string | Client-generated message ID for request-response correlation. |
| type | string | Dot-namespaced message type. |
| payload | object | Type-specific data. |

### Client → Core Messages

| Type | Payload Fields | Description |
|------|---------------|-------------|
| `chat.send` | thread_id?, content, attachments[] | Send user message. Omit thread_id for Main. |
| `chat.abort` | thread_id? | Abort current agent loop |
| `thread.create` | title?, type? | Create new Thread (type: "task" or "focus") |
| `thread.list` | limit?, offset? | List Threads |
| `thread.delete` | thread_id | Delete Thread |
| `tool.approve` | approval_id, approved | Approve or deny a tool call |
| `config.get` | key? | Get config value (null = all) |
| `config.set` | key, value | Set a live config value |

### Core → Client Messages

| Type | Payload Fields | Description |
|------|---------------|-------------|
| `chat.delta` | thread_id?, message_id, delta | Streaming token. Omit thread_id for Main. |
| `chat.done` | thread_id?, message_id, finish_reason | Stream complete |
| `chat.error` | thread_id?, error, code | Error during chat |
| `tool.request` | approval_id, thread_id?, tool_name, parameters, risk_level | Tool call approval request |
| `tool.progress` | thread_id?, tool_name, progress | Tool execution progress |
| `tool.result` | thread_id?, tool_name, result, is_error | Tool execution result |
| `thread.updated` | thread_id, title?, status? | Thread metadata changed |
| `automation.run_started` | run_id, subscription_name, trigger_event | Automation Run started |
| `automation.run_completed` | run_id, subscription_name, status, summary | Automation Run finished |
| `automation.approval` | run_id, approval_id, description, tools_used | Automation needs user approval for write operations |
| `event.injected` | thread_id?, event | Event injected into context |

## REST Endpoints

### System

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/health | Health check. Returns Core version, uptime, DB status. |

### Threads

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/threads | List Threads (paginated) |
| POST | /api/v1/threads | Create Thread |
| GET | /api/v1/threads/{id} | Get Thread detail |
| DELETE | /api/v1/threads/{id} | Delete Thread |

### Main

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/main/messages | Get Main conversation messages (paginated, most recent first) |

### Skills

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/skills | List installed Skills with status |
| GET | /api/v1/skills/{name} | Get Skill detail and manifest |
| POST | /api/v1/skills/{name}/enable | Enable a Skill |
| POST | /api/v1/skills/{name}/disable | Disable a Skill |

### Automation

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/automation/triggers | List registered triggers |
| GET | /api/v1/automation/subscriptions | List subscriptions |
| POST | /api/v1/automation/subscriptions | Create a subscription |
| DELETE | /api/v1/automation/subscriptions/{id} | Remove a subscription |
| GET | /api/v1/automation/routines | List available routines |
| GET | /api/v1/automation/runs | List recent Automation Runs |
| GET | /api/v1/automation/runs/{id} | Get Automation Run detail |
| GET | /api/v1/automation/events | Read Event Queue (paginated) |

### Configuration

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/config | Get full config (secrets redacted) |
| POST | /api/v1/config/reload | Re-read config file, apply reload + live changes. Returns diff of what changed and what requires restart. |

### Nodes (Phase 4)

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/nodes | List connected nodes |
| POST | /api/v1/nodes/pair | Pair a node device |
| DELETE | /api/v1/nodes/{node_id} | Remove a node |
| DELETE | /api/v1/nodes/{node_id}/token | Revoke node auth token |

### Webhooks (Phase 3)

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/hooks/{trigger_name}/{event_source} | Receive external webhook, publish to Event Queue |

Webhook endpoints are auto-registered when a Trigger with `type: webhook`
is installed. The endpoint validates the payload against the Trigger's
event schema and publishes a typed event to the Event Queue.

## WS vs REST Boundary

**WebSocket** is for anything that involves ongoing state or real-time flow:
chat streaming, tool approval/result cycles, config changes that should notify
connected clients, automation run notifications, and event injection.

**REST** is for stateless, request-response operations: health checks, listing
resources, CRUD on Threads/Skills/Automations, config reload, and incoming
webhooks.

**Overlap rule**: Threads and config are accessible via both channels.
When the same operation is available on both, REST is the canonical source and
WebSocket is a convenience for connected clients. If a REST call modifies state,
Core broadcasts the change to connected WebSocket clients as an update message.

## Error Codes

All errors include a `code` field (string) and a human-readable `error` field.

| Code | HTTP | Description |
|------|------|-------------|
| `auth_required` | 401 | No token provided |
| `auth_invalid` | 401 | Token is invalid or expired |
| `not_found` | 404 | Resource does not exist |
| `validation_error` | 422 | Invalid payload or parameters |
| `thread_not_found` | 404 | Thread ID does not exist |
| `skill_not_found` | 404 | Skill name does not exist |
| `skill_disabled` | 403 | Skill exists but is not enabled |
| `approval_timeout` | 408 | Tool call approval not received in time |
| `approval_denied` | 403 | User denied the tool call |
| `tool_error` | 500 | Tool execution failed |
| `resource_busy` | 409 | Resource locked by another session (Spec 07) |
| `rate_limited` | 429 | Too many requests |
| `config_invalid` | 422 | Config value failed validation |
| `config_restart_required` | 200 | Config changed but requires container restart to take effect |
| `automation_disabled` | 403 | Automation subscription exists but is disabled |
| `trigger_not_found` | 404 | Trigger name does not exist |
| `routine_not_found` | 404 | Routine file does not exist |
| `internal_error` | 500 | Unexpected server error |

On WebSocket, errors are delivered as `chat.error` (for session-scoped errors)
or as a response payload with the same `id` as the request (for other errors).

## Finish Reasons

| Reason | Description |
|--------|-------------|
| `stop` | Model finished naturally |
| `tool_use` | Model wants to call a tool (agent loop continues) |
| `max_tokens` | Context or response token limit reached |
| `error` | Error during generation |
| `aborted` | User sent `chat.abort` |

## Tool Approval

### Risk Levels

Every tool declares a `risk_level`. This applies universally — whether the tool
is called interactively (user present) or by an Automation (background).

| Risk Level | Meaning | Examples |
|------------|---------|---------|
| `low` | Read-only, no side effects | Read a file, check calendar |
| `medium` | Writes data, reversible | Create a calendar event, send a draft |
| `high` | System changes, hard to reverse | Delete files, execute shell commands |
| `critical` | Destructive or irreversible | Bulk delete, send emails on behalf of user |

### Approval Modes

Configured via `security.tool_approval` in config.

| Mode | Behavior |
|------|----------|
| `ask_first` | Every tool call sends `tool.request` and waits for `tool.approve` |
| `auto` | All enabled tools auto-execute without approval |
| `auto_with_allowlist` | Allowlisted tools auto-execute, others require approval |

### Risk Level Override

Regardless of approval mode, `high` and `critical` tools always require explicit
user approval. This is a safety invariant that cannot be overridden.

| Risk Level | `ask_first` | `auto` | `auto_with_allowlist` |
|------------|-------------|--------|----------------------|
| `low` | Ask | Auto | Auto if allowlisted, else ask |
| `medium` | Ask | Auto | Auto if allowlisted, else ask |
| `high` | Ask | Ask | Ask |
| `critical` | Ask | Ask | Ask |

### Automation Runs

When an Automation Run executes tools in the background (no user present), the
same risk-level rules apply. The Automation inherits tool permissions — it does
not have its own permission scope.

- `low` and `medium` tools: execute according to the configured approval mode
- `high` and `critical` tools: pause the Automation Run, send
  `automation.approval` to Main, wait for user response

If the user is offline when an approval is needed, the Run is suspended until
the user reconnects. Suspended Runs are visible in the sidebar.

## Type Definitions

See `packages/shared/doti_shared/models/protocol.py` for Pydantic models.
