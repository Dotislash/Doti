# Spec 03: Automation System

> Version: 1 | Status: Phase 3 Required | Last updated: 2026-03-07

## Overview

DOTI's automation system enables the agent to act proactively without user
interaction. It is built on four decoupled components connected through a
central Event Queue:

```
Triggers → Event Queue → Subscriptions → Agent (reads Routine, uses MCP tools)
```

This architecture deliberately separates "what tools exist" (Skills/MCP) from
"when and how to use them" (Automation). An Automation can use tools from any
installed Skill without permission conflicts.

## Architecture

### Three-Layer Model

```
┌────────────────────────────────────────────────────┐
│  Layer 1: MCP (Execution)                          │
│  Pure tools. Agent calls these to act.             │
│  ─ Built-in: filesystem, shell, web               │
│  ─ External: any MCP server (stdio/http)           │
│  ─ Each tool declares a risk_level                 │
├────────────────────────────────────────────────────┤
│  Layer 2: Skills (Knowledge + Capabilities)        │
│  Instructions + optional bundled MCP/scripts.      │
│  ─ SKILL.md: instructions the agent reads          │
│  ─ Optional: embedded MCP server (Skill-local)     │
│  ─ Optional: setup scripts                         │
│  ─ Used interactively or referenced by Routines    │
├────────────────────────────────────────────────────┤
│  Layer 3: Automation (Event-Driven)                │
│  Triggers → Event Queue → Subscriptions → Routines │
│  ─ Triggers: background scripts producing events   │
│  ─ Event Queue: central persistent bus             │
│  ─ Subscriptions: filter rules that wake the agent │
│  ─ Routines: instructions for autonomous execution │
└────────────────────────────────────────────────────┘
```

### Why This Separation

| Problem | Bundled model (e.g. "Kits") | DOTI's separated model |
|---------|----------------------------|----------------------|
| Automation needs tools from multiple sources | Cross-package permission conflicts | Automation uses any tool; permissions are per-tool |
| Same tools, different automation permissions | Cannot scope per-automation | Each Subscription inherits tool risk_level independently |
| Change a Routine but keep the Trigger | Must repackage everything | Change the Routine file only |
| Add a new Trigger for an existing Routine | Must modify the package | Create a new Subscription pointing to the same Routine |
| Skill updates a tool signature | All automations using this Skill break | Only Subscriptions referencing that specific tool are affected |

## Components

### Triggers

A Trigger is a long-running background process that produces events. It runs
continuously and pushes events to the Event Queue when conditions are met.

Triggers are intentionally simple — they detect conditions and emit events.
They contain no logic about what to do with those events.

#### Built-in Trigger Types

| Type | Description | Event Type |
|------|-------------|------------|
| `cron` | Time-based scheduling (cron expressions) | `cron.fired` |
| `heartbeat` | Periodic health/status check | `heartbeat.tick` |
| `file_watch` | Filesystem change detection | `file.changed` |
| `webhook` | External HTTP callback (Phase 3) | `webhook.received` |
| `threshold` | Metric exceeds a limit (Phase 3) | `threshold.exceeded` |

#### Trigger Definition

```json
{
  "name": "morning-check",
  "type": "cron",
  "config": {
    "expression": "0 8 * * *",
    "timezone": "America/New_York"
  },
  "enabled": true
}
```

#### Trigger Event Format

Every event pushed to the queue follows a standard envelope:

```json
{
  "id": "evt_01HXYZ",
  "type": "cron.fired",
  "source": "morning-check",
  "timestamp": "2026-03-07T08:00:00Z",
  "payload": {
    "scheduled_time": "2026-03-07T08:00:00-05:00"
  }
}
```

### Event Queue

The Event Queue is a persistent, ordered collection of events. All triggers
push to this single queue. Consumers (Subscriptions) read from it.

#### Properties

- **Persistent**: Events are written to storage before acknowledgment. No event
  is lost on crash.
- **Ordered**: Events are processed in insertion order.
- **Inspectable**: The queue is readable via REST API (`GET /api/v1/automation/events`).
- **Retention**: Events are retained for a configurable duration (default: 7 days),
  then pruned.

#### MVP Implementation

In Phase 1, the Event Queue is an in-memory `asyncio.Queue` backed by a JSONL
file for persistence. Events are appended on write and replayed on startup.

In later phases, this can be upgraded to SQLite-backed storage with proper
indexing and retention policies.

### Subscriptions

A Subscription is a rule that filters the Event Queue and wakes the agent when
a matching event appears. It binds a Trigger's events to a Routine.

#### Subscription Definition

```json
{
  "id": "sub_01HXYZ",
  "name": "morning-email-triage",
  "enabled": true,
  "filter": {
    "event_type": "cron.fired",
    "source": "morning-check"
  },
  "routine": "routines/email-triage.md",
  "output": {
    "target": "main",
    "notify": true
  }
}
```

#### Filter Matching

Filters match against event fields:

| Field | Operator | Example |
|-------|----------|---------|
| `event_type` | Exact match | `"cron.fired"` |
| `source` | Exact match or glob | `"morning-*"` |
| `payload.*` | JSONPath match (Phase 3) | `"payload.path endsWith .md"` |

MVP supports `event_type` and `source` exact match only.

#### Execution

When a Subscription matches an event:

1. Core creates a dedicated Thread for the Automation Run
2. The Thread loads the referenced Routine as its initial instructions
3. The agent reads the Routine and uses whatever MCP tools it needs
4. Tool approval follows the standard risk-level model (Spec 01)
5. On completion, the Thread is archived and a summary is posted to Main

#### Output Targets

| Target | Behavior |
|--------|----------|
| `main` | Post completion summary to Main conversation |
| `silent` | Archive the Run without posting to Main |
| `notify` | Post to Main only if the agent has something to report |

### Routines

A Routine is a Markdown file containing instructions for autonomous execution.
It is functionally identical to a Skill's instructions, but designed for
background use — it does not assume a user is present.

#### Routine Format

```markdown
# Email Triage

## Goal
Organize the inbox by categorizing unread emails and archiving spam.

## Steps
1. Use `email.list` to fetch all unread emails from the last 24 hours
2. Categorize each email:
   - **Urgent**: from known contacts with "urgent" or "asap" in subject
   - **Normal**: all other legitimate emails
   - **Spam**: promotional, newsletters not in allowlist
3. For spam emails, use `email.archive` to archive them
4. Summarize results: count per category, list urgent emails with sender and subject

## Output
Report the summary. If there are urgent emails, list them with sender and subject line.
If no action was needed, respond with a brief "inbox is clean" message.
```

#### Routine Location

Routines are stored in `workspace/routines/`. The path in a Subscription is
relative to the workspace root.

#### Routine vs Skill Instructions

| Aspect | Skill Instructions | Routine |
|--------|-------------------|---------|
| Triggered by | User request in conversation | Subscription matching an event |
| User present | Yes | No |
| Execution context | Main or user-created Thread | Dedicated Automation Thread |
| Can ask user questions | Yes | Only via approval requests |
| Tools available | All enabled tools | All enabled tools (same) |

## Automation Runs

An Automation Run is the execution record of a Subscription being triggered.
It replaces the "Kit Run" concept.

### Run Lifecycle

```
Event matched by Subscription
  → Run created (status: running)
    → Dedicated Thread created
      → Agent reads Routine
        → Agent uses MCP tools
          ├── low/medium tools: auto-execute per config
          ├── high/critical tools: pause, send approval to Main
          │     → User approves → continue
          │     → User denies → Run fails gracefully
          └── Agent completes Routine
            → Summary posted to Main (if configured)
              → Thread archived
                → Run status: completed
```

### Run States

| State | Description |
|-------|-------------|
| `running` | Automation is actively executing |
| `waiting_approval` | Paused waiting for user to approve a high-risk tool call |
| `completed` | Finished successfully |
| `failed` | Encountered an error |
| `cancelled` | User cancelled the Run |

### Run Record

```json
{
  "id": "run_01HXYZ",
  "subscription": "morning-email-triage",
  "trigger_event": { "type": "cron.fired", "source": "morning-check" },
  "started_at": "2026-03-07T08:00:01Z",
  "completed_at": "2026-03-07T08:02:34Z",
  "status": "completed",
  "thread_id": "thread_01HABC",
  "tools_called": [
    { "name": "email.list", "risk": "low", "approved": true },
    { "name": "email.archive", "risk": "medium", "approved": true }
  ],
  "summary": "Triaged 23 emails: 2 urgent, 18 normal, 3 archived as spam."
}
```

### Runs in the UI

Automation Runs appear in the sidebar:

```
┌─────────────────────────┐
│  Main                   │
├─────────────────────────┤
│  Automation Runs        │
│    Email triage (2m ago) │
│    Calendar brief (6h)  │
│    File backup (failed) │
├─────────────────────────┤
│  + New Thread           │
│    Task / Focus         │
├─────────────────────────┤
│  ACTIVE THREADS         │
│  Refactor auth module   │
│  Rust vs Go research    │
├─────────────────────────┤
│  ARCHIVED               │
│  Email cleanup (2/23)   │
│  API design (2/20)      │
└─────────────────────────┘
```

## Permissions

Automations do **not** have their own permission scope. They inherit the
standard tool risk-level model from Spec 01.

This is a deliberate design choice. The alternative — per-automation permission
scoping — creates the same cross-package permission conflicts that the bundled
Kit model had. By inheriting tool-level permissions, an Automation can freely
use tools from any Skill, and the user's permission preferences apply uniformly.

### Interactive vs Automation Approval

The only difference between interactive and automation tool approval is the
user's presence:

| Scenario | User present | Approval flow |
|----------|-------------|---------------|
| Interactive (Main/Thread) | Yes | `tool.request` → user clicks approve → `tool.approve` |
| Automation Run | No | Same risk rules apply. Low/medium: auto per config. High/critical: Run pauses, approval posted to Main. |

When a user is offline and an Automation Run needs approval, the Run is
suspended. When the user reconnects, pending approvals appear in Main.

## Phase Mapping

| Feature | Phase |
|---------|-------|
| Event Queue (in-memory + JSONL persistence) | 1 |
| Cron Trigger | 1 |
| Heartbeat Trigger | 1 |
| Subscriptions (exact match filter) | 1 |
| Routines (Markdown files) | 1 |
| Automation Runs (basic lifecycle) | 1 |
| Automation Runs in sidebar UI | 1 |
| File Watch Trigger | 2 |
| Webhook Trigger | 3 |
| Threshold Trigger | 3 |
| Advanced Subscription filters (JSONPath) | 3 |
| Subscription management UI | 2 |
| Run history and search | 2 |

## Type Definitions

See `packages/shared/doti_shared/models/automation.py` for Pydantic models.
