# DOTI Interaction Model

> Status: Final Discussion Document | Date: 2026-03-07 (revised)

This document describes how a user interacts with DOTI. It replaces the
traditional session-based chat model with a continuous, memory-driven
relationship between user and agent. It covers the Main conversation, Threads,
Automation, and the permission system.

---

## 1. Design Philosophy

### The Problem with Sessions

Every major AI chat product forces users to manage their own context. The user
faces a constant dilemma: start a new session to save tokens, or keep the
current one to preserve continuity. Neither choice is good. Frequent new
sessions lose context. Long sessions bloat cost and degrade quality.

Even products that add cross-session memory search don't solve the problem —
they increase context pressure rather than reducing it. The user still decides
when to split, when to continue, and when to manually re-introduce prior
context.

### DOTI's Answer

**Remove sessions entirely.** The agent maintains a single, continuous
relationship with the user. Context management is the system's responsibility.
The user never creates, names, switches, or deletes conversations.

The user opens DOTI and talks. The agent remembers what matters, forgets what
doesn't, and manages its own context window. When a task is complex enough to
need its own workspace, the agent creates one. When the task is done, the
workspace is archived and its results flow back into the agent's memory.

This means:

- No `/new` command. No "New Chat" button in the default flow.
- No session list to manage. No decision about which session to continue.
- No manual context summarization. No copy-pasting from old conversations.
- The agent handles context compression, memory retrieval, and workspace
  lifecycle automatically.

### Three Layers of Interaction

DOTI's interface is organized around three distinct information layers:

**Main** — The user's ongoing conversation with the agent. Handles all
day-to-day interaction. This is "talking to your assistant."

**Threads** — Scoped workspaces for complex tasks. Created when a job needs
focus, isolation, or parallel execution. This is "giving your assistant a
specific project."

**Automation Runs** — Execution records of triggered automations. Visible for
monitoring and review. This is "checking what your assistant did on autopilot."

These three layers form a natural user journey:

```
Daily conversation (Main)
  → Complex task identified → Thread created
    → Task completed → Thread archived, summary returns to Main
      → Pattern recognized → Routine + Subscription created (Phase 3)
        → Automation runs on schedule → Automation Run visible for monitoring
          → Automation Run results surface in Main
```

---

## 2. Main

Main is the default, always-on conversation surface.

### Properties

- **Singular.** One Main per DOTI instance. There is no "create new session."
- **Shared.** All connected devices in normal mode see the same conversation
  stream in real-time.
- **Persistent.** Main never resets. The agent manages its own context through
  automatic compression and long-term memory.
- **Always available.** Opening DOTI on any device drops the user into Main.

Main is not named or numbered. It is the default — the way you walk up to
your assistant and start talking without opening a ticket first.

### What Main Handles

Main handles everything that does not require a dedicated workspace:

- Quick questions and answers
- Brief tool use (check calendar, look up a file, search the web)
- Casual conversation
- Automation Run approvals and notifications
- Thread creation prompts and completion summaries

The boundary is: **if the task can be completed in a few exchanges without
significant context accumulation, it stays in Main.**

### Main's Access to Threads

The Main agent has a tool to query completed Thread conversations. This allows
it to reference past work without carrying the full context:

- `thread.search(query)` — semantic search across archived Threads
- `thread.read(thread_id)` — read full conversation history of a Thread

This provides a soft bridge between Main and Threads without merging their
context windows.

### Multi-Device Behavior

All devices connected in normal mode share one unified conversation stream.

- Messages are ordered by Core receipt time. If two devices send
  simultaneously, Core serializes them (first-in, first-processed).
- All connected clients receive all messages in real-time via WebSocket.
- Phase 1 supports serial processing only — one message processed at a time.

### Context on Reconnection

When a client reconnects to Main (after closing the browser, losing network,
etc.), Core restores context by loading:

1. The most recent compression summary (a condensed representation of older
   conversation history)
2. The last N raw messages (recent exchanges in full)

This means the agent is never starting from zero. It has a "recap" of prior
context plus recent history. The value of N and compression behavior are
configurable.

In Phase 1 this is the extent of memory — no semantic long-term recall. In
Phase 3, reconnection also triggers retrieval of relevant long-term memories
via embedding search.

---

## 3. Threads

A Thread is a scoped workspace for a task that needs more room than Main
provides.

### When Threads Are Created

There are three creation paths:

**Agent-initiated.** The user describes a complex task in Main. The agent
recognizes it needs a dedicated workspace — the task involves multiple steps,
batch operations, extended tool use chains, or sustained focus. The agent
proposes creating a Thread, and if the user agrees, the agent creates it and
passes the first prompt automatically.

In Main, this appears as an assistant message: a brief explanation of what
the Thread is for, plus a button to enter it.

**Agent-offered.** In less clear-cut cases, the agent offers a button in Main
that lets the user click into a new Thread. The user decides whether to use it.

**Manual.** The user creates a Thread directly from the sidebar. No message
appears in Main — the user is managing their own workflow.

The agent's judgment about when to suggest a Thread is hardcoded in the system
prompt for Phase 1, with plans to make it configurable later.

### Thread Types

Threads come in two types. The agent recommends a type based on the user's
described intent, but the user can override the recommendation at creation
time or switch type mid-thread.

**Task** — For work that involves the user personally. Organizing emails,
managing files, working through homework, handling personal or professional
tasks. The agent pulls in full personal context: preferences, history,
relevant memories.

**Focus** — For objective research and analysis. Investigating a technical
question, comparing options, deep-diving into a topic. The agent aggressively
prunes personal context to maximize objectivity and task-relevant information.

The distinction is purely about context injection strategy — what memories and
context the agent loads into the Thread's working window. Both types have
identical capabilities in terms of tool access.

### Thread Lifecycle

```
Created ──→ Active ──→ Completing ──→ Archived
                │           │
                │           └──→ Convert to Automation (Phase 3)
                │
                └──→ Paused (connection lost)
                        │
                        ├──→ Resumed (user reconnects via URL or sidebar)
                        └──→ Auto-archived (configurable timeout)
```

**Active.** The Thread has its own context window, managed independently from
Main. The agent can use all enabled tools (subject to the normal risk-level
approval rules). Only one device can actively interact with a given Thread at a
time. Other devices see the Thread in the sidebar but marked as "in use."

**Paused.** If the user disconnects (closes browser, loses network), the Thread
state is preserved server-side. Main shows a reminder that the user has an
unfinished task. The user can resume by clicking the sidebar entry or
navigating to the Thread's URL. After a configurable timeout, the Thread
auto-archives with whatever context it has, and the agent writes a summary to
memory noting the task was incomplete.

**Completing.** When the task approaches completion, the Thread's agent
proactively suggests wrapping up and archiving. The user confirms.

**Archived.** The agent generates two outputs:

1. A **task summary** — a descriptive paragraph of what was accomplished in the
   Thread, plus any extracted memory points (facts, preferences, decisions
   worth remembering). These are written to the memory system.

2. An **assistant message in Main** — a brief, natural-language recap injected
   into Main's conversation as if the agent is reporting back. This message
   serves two purposes: it gives the agent an opportunity to ask follow-up
   questions ("How did the meeting go after we prepped those notes?"), and it
   provides a smooth UX transition for the user returning to Main.

The archived Thread disappears from the active section of the sidebar but
remains accessible under the archived section. Its full conversation history
is stored and searchable.

### Thread Concurrency

Multiple Threads can be active in parallel. There is no artificial limit. A
user could have a Task Thread for email cleanup and a Focus Thread for
technical research running simultaneously on different devices (or different
tabs on the same device).

### Thread Visibility

- **Task and Focus Threads** are visible in the sidebar on all devices.
- **Privacy and Incognito Threads** (see below) are visible only on the
  originating device.

---

## 4. Privacy and Incognito Modes

These are not Thread types — they are **connection modes** that create
ephemeral, isolated workspaces.

### Privacy Mode

**Use case:** "I want to ask something without the agent remembering it later."

- Can read existing memory (the agent still knows who you are)
- Does not write to memory (nothing from this conversation persists)
- Conversation is destroyed on exit
- All tool use requires approval (overrides any `auto` setting)
- Visible only on the originating device
- Other devices continue in whatever mode they were in

### Incognito Mode

**Use case:** "Let someone else use my agent" or "Start completely clean."

- Cannot read memory (the agent knows nothing about the user)
- Does not write to memory
- Conversation is destroyed on exit
- All tool use requires approval
- Visible only on the originating device
- Other devices continue in whatever mode they were in

### Isolation Behavior

While a device is in Privacy or Incognito mode, it does **not** see Main
updates. The device is fully isolated. Upon exiting the mode, the device syncs
back to Main's current state.

Automation triggers continue to fire normally while a user is in
Privacy/Incognito mode. Trigger results are written to memory as system events
(since they are system-level, not user-level activity) but are not injected
into the isolated context.

---

## 5. Automation and Permissions

### Tool Risk Levels

DOTI uses a single, unified permission system based on tool risk levels. This
applies everywhere — interactive use in Main/Threads and background Automation
Runs.

| Risk Level | Meaning | Examples |
|------------|---------|---------|
| `low` | Read-only, no side effects | Read a file, check calendar |
| `medium` | Writes data, reversible | Create calendar event, send draft |
| `high` | System changes, hard to reverse | Delete files, execute shell |
| `critical` | Destructive or irreversible | Bulk delete, send emails as user |

The `security.tool_approval` config (`ask_first` / `auto` / `auto_with_allowlist`)
determines which risk levels require per-tool approval. `high` and `critical`
always require approval regardless of config — this is a safety invariant.

### Interactive Use (User Present)

When the user is in Main or a Thread and the agent calls a tool, the standard
risk-level approval applies. The agent sends a `tool.request`, the user sees
the request in the UI, and approves or denies.

### Automation Use (Background)

When an Automation Run executes (triggered by a Subscription matching an event),
the same risk-level rules apply. The Automation does not have its own permission
scope — it inherits from the tool declarations.

- `low` and `medium` tools: execute according to the configured approval mode
- `high` and `critical` tools: the Run pauses, an approval request appears in
  Main, and the user approves or denies

If the user is offline when approval is needed, the Run is suspended until
reconnection. Pending approvals are shown in the sidebar and in Main.

### Why One System, Not Two

The original design considered separate permission systems for interactive use
and automation (the "Kit" model). This was abandoned because:

1. **Cross-package permissions are intractable.** When an automation needs tools
   from multiple packages, no single package "owns" the permission scope.
2. **Per-tool risk levels are sufficient.** A tool that's dangerous interactively
   is also dangerous in automation. The risk is inherent to the tool, not the
   context.
3. **Simpler mental model.** Users learn one system: "high-risk tools always
   ask, low-risk tools follow my config."

### Automation Approval in Main

When a running Automation needs user approval, the approval request appears in
Main. The Main agent acts as a translator — it does not simply forward a raw
tool call request. Instead, it:

1. Receives the Automation Run's context and the tool call it wants to make
2. Summarizes it in natural language with full context
3. Presents it to the user as a conversational message
4. Waits for the user's decision

This means the user never sees "`shell.exec` wants to run `rm -rf /tmp/old`."
Instead they see: "Your file cleanup automation wants to delete 47 temporary
files from `/tmp/old`. These are all older than 30 days. Approve?"

---

## 6. Automation Runs (Monitoring)

Every Automation execution produces an **Automation Run** — a structured record
of what happened. Automation Runs replace the earlier "Kit Run" concept.

### What a Run Contains

- Subscription that initiated the run
- Trigger event that matched
- Timestamp and duration
- Thread ID (dedicated Thread created for this Run)
- Tools called (with inputs, outputs, and risk levels)
- Approval status and user responses (if any approvals were needed)
- Final outcome (completed, failed, waiting_approval, cancelled)
- Summary generated by the agent
- Errors, if any

### Runs in the UI

Automation Runs appear in the sidebar between Main and the Thread list:

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
│    Privacy / Incognito  │
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

Clicking an Automation Run opens a detail view — not a conversation, but an
execution log showing each step, its inputs/outputs, timing, and status. This
is a monitoring interface, not a chat interface.

A Run that is awaiting approval shows a badge in the sidebar, and its approval
request appears in Main as described in the previous section.

---

## 7. The Conversation-to-Automation Loop

One of DOTI's goals is the ability to turn interactive work into automated
routines. The full loop:

```
1. User works with agent in a Thread
   "Help me organize my email every week"
   → Agent and user iterate on the approach
   → Agent uses email tools to sort, label, archive

2. Thread completes and is archived
   → Summary written to memory
   → Full conversation history preserved

3. User (or agent) suggests creating an Automation (Phase 3)
   → Agent retrieves the archived Thread
   → Analyzes tool call patterns, instructions, decision logic
   → Generates:
     - A Routine (markdown instructions for the task)
     - A Trigger (cron schedule for weekly execution)
     - A Subscription (binding the trigger to the routine)

4. Automation goes live
   → Subscription registered
   → Trigger starts running
   → First Run executes in a dedicated Thread
   → Results posted to Main for review

5. Automation runs weekly on its own
   → low/medium tools: auto-execute per config
   → high/critical tools: pause and ask user in Main
```

The user taught the agent how to do something through natural conversation.
The agent codified that into a Routine. A Trigger and Subscription were created
to run it on schedule. The permission model is inherited from tool risk levels —
no separate trust system needed.

---

## 8. Memory Architecture

### Phase 1 (Simplified)

- **Active context.** Current message history in Main or a Thread, held in
  memory and sent to the LLM.
- **Context compression.** When token count approaches `compression_threshold`,
  the long_context model compresses older messages into a summary prefix.
- **Reconnection recovery.** Main loads the most recent compression summary
  plus last N raw messages.
- **Thread search.** Main agent can query archived Thread conversations via
  `thread.search` and `thread.read` tools.
- **Stored but not recalled.** All messages are persisted to the database for
  future Phase 3 indexing. Archived Threads are browsable but the agent cannot
  automatically retrieve them (must use search tools explicitly).

### Phase 3 (Full)

- **Long-term memory.** Vector-embedded semantic store built from Main
  history, Thread summaries, and system events (Automation Run results,
  trigger outputs).
- **Automatic recall.** On new connection or context switch, the agent
  retrieves relevant memories and injects them into context.
- **Memory management API.** User can view, search, and delete stored memories.
- **Thread summary writes.** Completed Threads automatically generate summaries
  and memory extractions that are written to the store.
- **Cross-context recall.** The agent in Main can search archived Threads. The
  agent in a Task Thread can recall relevant memories from Main and other
  archived Threads.

---

## 9. Impact on Existing Specs

### Spec 01: Core API Protocol

Updated in v3 to reflect this interaction model:

- Removed session-based message types. `chat.send` targets Main (no thread_id)
  or a specific Thread (with thread_id).
- Added Thread lifecycle messages: `thread.create`, `thread.list`,
  `thread.delete`.
- Added Automation messages: `automation.run_started`, `automation.run_completed`,
  `automation.approval`.
- Unified tool approval: `tool.request` / `tool.approve` used for both
  interactive and automation contexts.
- Updated error codes: added `automation_disabled`, `trigger_not_found`,
  `routine_not_found`.

### Spec 02: Config Format

Updated in v3:

- `security.kit_approval` → `security.tool_approval` (tools, not packages)
- `security.kit_allowlist` → `security.tool_allowlist`
- Added `workspace.path` for workspace root directory
- Added `automation.*` config section (triggers, subscriptions, routines_dir,
  retention settings)
- Agent profile role `kit` renamed to `automation`

### Spec 03: Automation System (New)

New spec covering the full automation architecture:
- Triggers, Event Queue, Subscriptions, Routines
- Automation Run lifecycle
- Permission inheritance model

### Spec 04: Storage Schema

New tables needed:

- `main_messages` — Main conversation history
- `threads` — Thread metadata (type, status, created_at, archived_at, etc.)
- `thread_messages` — Per-Thread message history
- `compression_snapshots` — Stored compression summaries for Main and Threads
- `automation_triggers` — Registered trigger definitions
- `automation_subscriptions` — Subscription rules
- `automation_events` — Event Queue entries
- `automation_runs` — Automation Run execution records
- `memory` (Phase 3) — Long-term memory entries with embeddings

### Spec 07: Concurrency Model

- Main serialization: one message at a time in Main.
- Thread isolation: each Thread has independent context and processing.
- Thread locking: one active device per Thread at a time.
- Automation Run concurrency: multiple Runs can execute in parallel, but
  resource-level locking (Spec 07 existing design) prevents conflicts.

---

## 10. Phase Mapping

| Feature | Phase |
|---------|-------|
| Main conversation (sessionless, unified stream) | 1 |
| Basic context compression | 1 |
| Main reconnection (summary + last N messages) | 1 |
| Thread creation (Task, Focus) — agent-initiated and manual | 1 |
| Thread lifecycle (active, paused, auto-archive) | 1 |
| Thread archival with summary → Main message | 1 |
| Thread search tools for Main agent | 1 |
| Privacy and Incognito modes | 1 |
| Sidebar (Main, Automation Runs, Threads) | 1 |
| Multi-device Main sync | 1 |
| Tool approval (risk-level based, unified system) | 1 |
| Automation: Cron Trigger + Heartbeat Trigger | 1 |
| Automation: Event Queue (in-memory + JSONL) | 1 |
| Automation: Subscriptions (exact match) | 1 |
| Automation: Routines (Markdown files) | 1 |
| Automation: Basic Run lifecycle | 1 |
| Automation: Run monitoring in sidebar | 1 |
| Agent-suggested Thread creation (smart detection) | 2 |
| Automation: File Watch Trigger | 2 |
| Automation: Subscription management UI | 2 |
| Automation: Run history and search | 2 |
| Long-term memory (embedding + recall) | 3 |
| Thread summary → memory writes | 3 |
| Cross-context recall | 3 |
| Thread → Automation conversion | 3 |
| Automation: Webhook Trigger | 3 |
| Automation: Threshold Trigger | 3 |
| Automation: Advanced filters (JSONPath) | 3 |
| Memory management API | 3 |

---

## 11. Decisions Log

| # | Question | Decision |
|---|----------|----------|
| 1 | Remove sessions? | Yes. Replace with Main + Threads. |
| 2 | Multi-client model? | Unified Main stream, shared across all devices. |
| 3 | Mode switching scope? | Per-connection. One device can be in Incognito while others are in Main. |
| 4 | Phase 1 memory depth? | Simplified: active context + compression. Full memory in Phase 3. |
| 5 | Triggers in Privacy/Incognito? | Fire normally. Results written to memory as system events. Not injected into isolated context. |
| 6 | Thread → Automation conversion phase? | Phase 3. |
| 7 | Task vs Focus selection? | Agent recommends based on described intent. User can override. |
| 8 | Thread concurrency? | Multiple Threads active in parallel, no limit. |
| 9 | Main reconnection? | Load most recent compression summary + last N raw messages. |
| 10 | Permission model? | Single unified system based on tool risk levels. No separate automation permissions. Replaces the earlier "two-system Kit model." |
| 11 | Tool approval invariant? | `high` and `critical` tools always require approval, regardless of config or context. |
| 12 | Automation background approval? | Run pauses, approval request posted to Main. If user offline, Run suspended until reconnection. |
| 13 | Thread creation rules? | Hardcoded in system prompt for Phase 1, configurable later. |
| 14 | Thread archival? | Agent proactively suggests. Summary + memory extraction on archive. Assistant message injected into Main for follow-up. |
| 15 | Privacy/Incognito tool approval? | Always `ask_first`, not configurable. Safety invariant. |
| 16 | Skills vs Kits? | Abandoned Kit model. Skills provide tools + instructions. Automation is a separate system (Triggers → Event Queue → Subscriptions → Routines). |
| 17 | Automation permissions? | Inherited from tool risk levels. No per-automation permission scope. |
| 18 | Main access to Threads? | Main agent has `thread.search` and `thread.read` tools to query archived Threads. |

---

## 12. Open Questions

1. **Thread naming.** "Thread" is the working term. Alternatives considered:
   workspace, branch, space, canvas. Needs final decision before UI work.

2. **Auto-archive timeout.** Default duration before a paused Thread
   auto-archives. Candidates: 12h, 24h, 72h, configurable.

3. **Reconnection N value.** How many recent raw messages to load on Main
   reconnection. Fixed or configurable? Depends on model context window?

4. **Automation Run failure.** If a Run fails or the user rejects an approval,
   what happens? Retry? Subscription stays active for the next trigger event?

5. **Thread-to-Thread references.** Can a Focus Thread retrieve context from
   an active Task Thread? Or strictly isolated, sharing only via memory?

6. **Spec structure.** This document covers the interaction model holistically.
   The final spec structure (whether this becomes Spec 03, gets folded into
   Spec 01, or splits across multiple specs) is TBD.

7. **Routine versioning.** When a Routine file is modified while a Subscription
   is active, should the next Run use the new version immediately, or require
   re-approval?
