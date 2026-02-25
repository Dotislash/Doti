# Spec 01: Core API Protocol

> Version: 2 | Status: Phase 1 Required | Last updated: 2026-02-23

## Overview

WebSocket primary channel for real-time interaction (streaming, approvals,
events). REST secondary channel for stateless operations (health, config,
Kit management). All WebSocket messages carry a protocol version number.

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
{"v": 2, "id": "msg_01HXYZ", "type": "chat.send", "payload": {...}}
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
| `chat.send` | session_id, content, attachments[] | Send user message |
| `chat.abort` | session_id | Abort current agent loop |
| `session.create` | title? | Create new session |
| `session.list` | limit?, offset? | List sessions |
| `session.delete` | session_id | Delete session |
| `kit.approve` | approval_id, approved | Approve or deny a tool call |
| `config.get` | key? | Get config value (null = all) |
| `config.set` | key, value | Set a live config value |

### Core → Client Messages

| Type | Payload Fields | Description |
|------|---------------|-------------|
| `chat.delta` | session_id, message_id, delta | Streaming token |
| `chat.done` | session_id, message_id, finish_reason | Stream complete |
| `chat.error` | session_id, error, code | Error during chat |
| `kit.request` | approval_id, session_id, kit_name, tool_name, parameters, risk_level | Tool call approval request |
| `kit.progress` | session_id, kit_name, tool_name, progress | Tool execution progress |
| `kit.result` | session_id, kit_name, tool_name, result, is_error | Tool execution result |
| `session.updated` | session_id, title? | Session metadata changed |
| `event.injected` | session_id, event | Event injected into session context |

## REST Endpoints

### System

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/health | Health check. Returns Core version, uptime, DB status. |

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/sessions | List sessions (paginated) |
| POST | /api/v1/sessions | Create session |
| GET | /api/v1/sessions/{id} | Get session detail |
| DELETE | /api/v1/sessions/{id} | Delete session |

### Kits

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/kits | List installed Kits with status |
| GET | /api/v1/kits/{name} | Get Kit detail and manifest |
| POST | /api/v1/kits/{name}/enable | Enable a Kit |
| POST | /api/v1/kits/{name}/disable | Disable a Kit |

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
| POST | /api/v1/hooks/{kit_name}/{event_source} | Receive external webhook, publish to event bus |

Webhook endpoints are auto-registered when a Kit with `trigger: webhook` event
sources is installed. The endpoint validates the payload against the Kit's
event source schema and publishes a typed event to the EventBus.

## WS vs REST Boundary

**WebSocket** is for anything that involves ongoing state or real-time flow:
chat streaming, tool approval/result cycles, config changes that should notify
connected clients, and event injection.

**REST** is for stateless, request-response operations: health checks, listing
resources, CRUD on sessions/Kits/nodes, config reload, and incoming webhooks.

**Overlap rule**: Sessions and config are accessible via both channels.
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
| `session_not_found` | 404 | Session ID does not exist |
| `kit_not_found` | 404 | Kit name does not exist |
| `kit_disabled` | 403 | Kit exists but is not enabled |
| `approval_timeout` | 408 | Tool call approval not received in time |
| `approval_denied` | 403 | User denied the tool call |
| `tool_error` | 500 | Tool execution failed |
| `resource_busy` | 409 | Resource locked by another session (Spec 07) |
| `rate_limited` | 429 | Too many requests |
| `config_invalid` | 422 | Config value failed validation |
| `config_restart_required` | 200 | Config changed but requires container restart to take effect |
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

## Kit Approval Modes

Configured via `security.kit_approval` in config.

| Mode | Behavior |
|------|----------|
| `ask_first` | Every tool call sends `kit.request` and waits for `kit.approve` |
| `auto` | All enabled Kit tools auto-execute without approval |
| `auto_with_allowlist` | Allowlisted Kit tools auto-execute, others require approval |

### Risk Levels and Approval Override

Each tool in a Kit manifest declares a `risk_level`. The approval mode interacts
with risk level as follows:

| Risk Level | `ask_first` | `auto` | `auto_with_allowlist` |
|------------|-------------|--------|----------------------|
| `low` | Ask | Auto | Auto if allowlisted, else ask |
| `medium` | Ask | Auto | Auto if allowlisted, else ask |
| `high` | Ask | Ask | Ask |
| `critical` | Ask | Ask | Ask |

`high` and `critical` tools always require explicit user approval regardless of
the configured mode. This is a safety invariant that cannot be overridden.

| Risk Level | Meaning | Examples |
|------------|---------|---------|
| `low` | Read-only, no side effects | Read a file, check calendar |
| `medium` | Writes data, reversible | Create a calendar event, send a draft |
| `high` | System changes, hard to reverse | Delete files, execute shell commands |
| `critical` | Destructive or irreversible | Format disk, bulk delete, send emails on behalf of user |

## Type Definitions

See `packages/shared/doti_shared/models/protocol.py` for Pydantic models.
