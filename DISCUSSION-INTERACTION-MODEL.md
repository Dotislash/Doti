# DOTI Interaction Model

> Status: Final Discussion Document | Date: 2026-02-24

This document describes how a user interacts with DOTI. It replaces the
traditional session-based chat model with a continuous, memory-driven
relationship between user and agent. It covers the Main conversation, Threads,
Kit automation, and the permission systems that tie them together.

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

**Kit Runs** — Execution records of automated Kit triggers. Visible for
monitoring and review. This is "checking what your assistant did on autopilot."

These three layers form a natural user journey:

```
Daily conversation (Main)
  → Complex task identified → Thread created
    → Task completed → Thread archived, summary returns to Main
      → Pattern recognized → Kit generated from Thread (Phase 3)
        → Kit runs automatically → Kit Run visible for monitoring
          → Kit Run results surface in Main
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
- Kit Run approvals and notifications
- Thread creation prompts and completion summaries

The boundary is: **if the task can be completed in a few exchanges without
significant context accumulation, it stays in Main.**

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
identical capabilities in terms of Kit access and tool use.

### Thread Lifecycle

```
Created ──→ Active ──→ Completing ──→ Archived
                │           │
                │           ├──→ Convert to Kit (Phase 3)
                │           └──→ Convert to Task item (Phase 3)
                │
                └──→ Paused (connection lost)
                        │
                        ├──→ Resumed (user reconnects via URL or sidebar)
                        └──→ Auto-archived (configurable timeout)
```

**Active.** The Thread has its own context window, managed independently from
Main. The agent can use all enabled Kits (subject to the normal interactive
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
- **Privacy and Incognito Threads** (see §4) are visible only on the
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

Kit triggers continue to fire normally while a user is in Privacy/Incognito
mode. Trigger results are written to memory as system events (since they are
system-level, not user-level activity) but are not injected into the isolated
context.

---

## 5. Kit Automation and the Two Permission Systems

DOTI has two completely independent permission systems. This is a critical
design distinction.

### System 1: Interactive Approval (User in Conversation)

When the user is present in Main or a Thread and the agent calls a Kit tool,
the existing risk-level system from Spec 01 applies:

| Risk Level | Meaning | Examples |
|------------|---------|---------|
| `low` | Read-only, no side effects | Read a file, check calendar |
| `medium` | Writes data, reversible | Create calendar event, send draft |
| `high` | System changes, hard to reverse | Delete files, execute shell |
| `critical` | Destructive or irreversible | Bulk delete, send emails as user |

The `security.kit_approval` config (`ask_first` / `auto` / `auto_with_allowlist`)
determines which risk levels require per-tool approval. `high` and `critical`
always require approval regardless of config.

**This system is unchanged from Spec 01.** It applies to any Kit tool call made
while the user is actively interacting — whether in Main, a Task Thread, or a
Focus Thread. The user is present, the context is clear, and per-tool approval
is appropriate.

### System 2: Automation Approval (Kit Runs in Background)

When a Kit's trigger fires and executes in the background (cron, webhook,
sensor, etc.), a completely different permission model applies. The user is
not present, so per-tool approval is inappropriate. Instead, the Kit goes
through a **structured admission process** before it is allowed to run
autonomously at all.

#### Automation Admission Flow

```
Kit installed
  │
  ├── Interactive tools available immediately
  │   (governed by System 1, risk-level approval)
  │
  └── Automation DISABLED by default
      (trigger code is NOT added to the event queue)
      │
      ▼
Main agent reviews the Kit's automation
  → Explains to user: "This Kit wants to run every morning at 8 AM
     to organize your email. It will use these tools: ..."
  → User agrees to enable automation
      │
      ▼
Trial run (one supervised execution)
  → Phase 1: Kit executes read-only operations, collects information
  → Phase 2: Kit presents its write plan to the main agent
  → Main agent summarizes the plan for the user in Main:
     "Your email Kit sorted 47 messages. 3 need permanent deletion.
      Here are the details. Approve?"
  → User reviews and approves the result
      │
      ▼
Automation activated
  → Kit snapshot taken (frozen version of manifest + code)
  → Trigger added to event queue
  → Subsequent runs execute according to their tool risk profile:
     - All-read Kit: fully automatic, no approval needed
     - Mixed Kit: read phase automatic, write plan submitted for approval
     - High-risk Kit: always submits for approval
      │
      ▼
Kit changes detected (any modification to manifest or code)
  → ALL automation for this Kit immediately disabled
  → Trigger removed from event queue
  → Must go through the full admission flow again
```

#### Why Two Systems

The interactive system (System 1) works because the user is present and has
full context about what they asked for. "Delete this file" → agent calls
`delete_file()` → user approves. The action is a direct response to the user's
request.

The automation system (System 2) works differently because the user is absent.
A Kit running at 3 AM cannot ask the user to approve each tool call in
real-time. Instead, it follows a trust model:

1. **Trust is earned.** No Kit gets automation privileges by default.
2. **Trust is version-locked.** The exact code that was approved is
   snapshotted. Any change revokes trust.
3. **Trust is graduated.** Read-only Kits get automatic trust. Write Kits
   earn it through successful trial runs.
4. **High-risk operations always come back to the user.** Even fully trusted
   Kits pause and ask when they encounter destructive operations.

#### Automation Approval in Main

When a running Kit needs user approval for its write plan, the approval
request appears in Main. The main agent acts as a translator — it does not
simply forward a raw tool call request. Instead, it:

1. Receives the Kit Run's collected information and proposed write plan
2. Summarizes it in natural language with full context
3. Presents it to the user as a conversational message
4. Waits for the user's decision

This means the user never sees "Kit `email-organizer` wants to call
`delete_email(id=msg_47abc)`. Allow?" Instead they see: "Your email Kit
finished its morning sweep. It organized 47 messages into folders and found
3 that look like spam. Want me to permanently delete those 3?"

#### Kit Snapshot and Change Detection

When a Kit's automation is activated, Core takes a snapshot of the Kit:

- Manifest hash (all declared tools, triggers, instructions)
- Code hash (MCP server implementation)

Before each automated run, Core compares the current Kit state against the
snapshot. If anything has changed — a tool was added, instructions were
modified, the MCP server code was updated — Core:

1. Removes the Kit's triggers from the event queue
2. Disables all automation for this Kit
3. Notifies the user in Main: "Kit [name] has been updated. Its automation
   has been paused. Would you like to review and re-enable it?"

The Kit's interactive tools remain available (governed by System 1). Only
the automation is affected.

---

## 6. Kit Runs (Monitoring)

Every Kit automation execution produces a **Kit Run** — a structured record
of what happened.

### What a Kit Run Contains

- Trigger that initiated the run (cron schedule, webhook event, sensor reading)
- Timestamp and duration
- Tools called (with inputs and outputs)
- Phase 1 (read) results
- Phase 2 (write) plan (if applicable)
- Approval status and user response (if approval was required)
- Final outcome (success, partial, failed, awaiting approval)
- Errors, if any

### Kit Runs in the UI

Kit Runs appear in the sidebar between Main and the Thread list:

```
┌─────────────────────────┐
│  ● Main                 │
├─────────────────────────┤
│  ⚡ Kit Runs             │
│    📧 Email digest (2m ago)
│    📅 Calendar brief (6h ago)
│    ⚠️ File backup (failed)
├─────────────────────────┤
│  + New Thread            │
│    Task / Focus / Privacy / Incognito
├─────────────────────────┤
│  ACTIVE THREADS          │
│  📋 Refactor auth module │
│  🔍 Rust vs Go research  │
├─────────────────────────┤
│  ARCHIVED                │
│  ✓ Email cleanup (2/23)  │
│  ✓ API design (2/20)     │
└─────────────────────────┘
```

Clicking a Kit Run opens a detail view — not a conversation, but an execution
log showing each step, its inputs/outputs, timing, and status. This is a
monitoring interface, not a chat interface.

A Kit Run that is awaiting approval shows a badge in the sidebar, and its
approval request appears in Main as described in §5.

---

## 7. The Conversation-to-Automation Loop

One of DOTI's defining features is the ability to turn interactive work into
automated routines. The full loop:

```
1. User works with agent in a Thread
   "Help me organize my email every week"
   → Agent and user iterate on the approach
   → Agent uses email Kit tools to sort, label, archive

2. Thread completes and is archived
   → Summary written to memory
   → Full conversation history preserved

3. User (or agent) suggests creating a Kit from this Thread (Phase 3)
   → Main agent retrieves the archived Thread
   → Analyzes tool call patterns, instructions, decision logic
   → Generates a Kit manifest with:
     - Trigger: cron (weekly)
     - Instructions: the sorting/labeling logic from the Thread
     - Tools: references to the email Kit's MCP tools

4. Kit goes through automation admission
   → Agent presents the Kit to the user
   → Trial run → approval → snapshot → automation enabled

5. Kit runs weekly on its own
   → Read phase: scan inbox, categorize
   → Write phase: submit plan to main agent → user approves (initially)
   → After N successful runs: write phase auto-approves for safe operations
```

The user taught the agent how to do something through natural conversation.
The agent codified that into a repeatable, automated process. The process
earned trust through supervised execution. Now it runs on its own.

---

## 8. Memory Architecture

### Phase 1 (Simplified)

- **Active context.** Current message history in Main or a Thread, held in
  memory and sent to the LLM.
- **Context compression.** When token count approaches `compression_threshold`,
  the long_context model compresses older messages into a summary prefix.
- **Reconnection recovery.** Main loads the most recent compression summary
  plus last N raw messages.
- **Stored but not recalled.** All messages are persisted to the database for
  future Phase 3 indexing. Archived Threads are browsable but the agent cannot
  automatically retrieve them.

### Phase 3 (Full)

- **Long-term memory.** Vector-embedded semantic store built from Main
  history, Thread summaries, and system events (Kit Run results, trigger
  outputs).
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

Major rewrite required.

- Remove all `session.*` message types and REST endpoints.
- `chat.send` no longer carries `session_id`. Instead, messages target either
  Main (default) or a specific Thread ID.
- Add Thread lifecycle messages: `thread.create`, `thread.pause`,
  `thread.resume`, `thread.complete`, `thread.archive`.
- Add mode switching: `mode.switch`, `mode.current`.
- Add Kit Run monitoring messages: `kit_run.status`, `kit_run.approval`.
- Replace `kit.request` / `kit.approve` flow for automation with the
  two-phase model (read results → write plan → approval in Main).
- Interactive Kit approval (`kit.request` / `kit.approve`) remains for
  System 1 (user-present) scenarios.
- Update error codes: `session_not_found` → `thread_not_found`, add
  `automation_disabled`, `snapshot_mismatch`, etc.

### Spec 02: Config Format

Add new configuration sections:

- `threads.auto_archive_timeout` — how long before a paused Thread
  auto-archives (e.g., `24h`)
- `threads.reconnection_messages` — value of N for Main reconnection
- `memory.*` — placeholder for Phase 3 memory configuration
- Privacy/Incognito modes: hardcoded to `ask_first` approval, not
  configurable (safety invariant)

### Spec 04: Storage Schema

New tables needed:

- `main_messages` — Main conversation history (replaces `sessions` /
  `session_messages`)
- `threads` — Thread metadata (type, status, created_at, archived_at, etc.)
- `thread_messages` — Per-Thread message history
- `compression_snapshots` — Stored compression summaries for Main and Threads
- `kit_runs` — Kit automation execution records
- `kit_snapshots` — Frozen Kit state for automation trust verification
- `memory` (Phase 3) — Long-term memory entries with embeddings

### Spec 05: Kit Manifest

Add automation-related declarations:

- Two-phase execution structure: which tools are read-phase, which are
  write-phase
- Automation instructions (what the Kit should do when triggered, as distinct
  from interactive usage instructions)
- Snapshot-compatible versioning (manifest hash support)
- Origin metadata for Kits generated from Threads (Phase 3)

### Spec 07: Concurrency Model

- Main serialization: one message at a time in Main.
- Thread isolation: each Thread has independent context and processing.
- Thread locking: one active device per Thread at a time.
- Kit Run concurrency: multiple Kit Runs can execute in parallel, but
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
| Privacy and Incognito modes | 1 |
| Sidebar (Main, Kit Runs, Threads) | 1 |
| Multi-device Main sync | 1 |
| Kit interactive approval (System 1, risk-level) | 1 |
| Kit automation admission flow | 2 |
| Kit two-phase execution (read → write plan → approve) | 2 |
| Kit snapshot and change detection | 2 |
| Kit Run monitoring UI | 2 |
| Agent-suggested Thread creation (smart detection) | 2 |
| Long-term memory (embedding + recall) | 3 |
| Thread summary → memory writes | 3 |
| Cross-context recall | 3 |
| Thread → Kit conversion | 3 |
| Thread → Task item (to-do + background job) | 3 |
| Kit auto-trust upgrade (N successful runs) | 3 |
| Memory management API | 3 |

---

## 11. Decisions Log

| # | Question | Decision |
|---|----------|----------|
| 1 | Remove sessions? | Yes. Replace with Main + Threads. |
| 2 | Multi-client model? | Unified Main stream, shared across all devices. |
| 3 | Mode switching scope? | Per-connection. One device can be in Incognito while others are in Main. |
| 4 | Phase 1 memory depth? | Simplified: active context + compression. Full memory in Phase 3. |
| 5 | Kit triggers in Privacy/Incognito? | Fire normally. Results written to memory as system events. Not injected into isolated context. |
| 6 | Thread → Kit conversion phase? | Phase 3. |
| 7 | Thread → Task item meaning? | Both to-do (agent follows up) and background job (agent continues async), depending on task nature. |
| 8 | Task vs Focus selection? | Agent recommends based on described intent. User can override. |
| 9 | Thread concurrency? | Multiple Threads active in parallel, no limit. |
| 10 | Main reconnection? | Load most recent compression summary + last N raw messages. |
| 11 | Kit interactive vs automation approval? | Two independent systems. Interactive: per-tool risk-level (Spec 01). Automation: two-phase admission + snapshot trust. |
| 12 | Kit automation default? | Disabled on install. Requires agent review → user approval → trial run → snapshot before activation. |
| 13 | Kit automation on change? | Immediately disabled. All triggers removed. Must re-run full admission flow. |
| 14 | Kit auto-trust upgrade? | Read-only Kits: automatic trust. Mixed Kits: trust earned after N successful runs. High-risk: always requires approval. |
| 15 | Thread creation rules? | Hardcoded in system prompt for Phase 1, configurable later. |
| 16 | Thread archival? | Agent proactively suggests. Summary + memory extraction on archive. Assistant message injected into Main for follow-up. |
| 17 | Privacy/Incognito tool approval? | Always `ask_first`, not configurable. Safety invariant. |

---

## 12. Open Questions

1. **Thread naming.** "Thread" is the working term. Alternatives considered:
   workspace, branch, space, canvas. Needs final decision before UI work.

2. **Auto-archive timeout.** Default duration before a paused Thread
   auto-archives. Candidates: 12h, 24h, 72h, configurable.

3. **Reconnection N value.** How many recent raw messages to load on Main
   reconnection. Fixed or configurable? Depends on model context window?

4. **Background jobs (Phase 3).** When a Thread converts to a background job,
   where do results appear? Main notification? Memory only? Dedicated UI?

5. **Thread-to-Thread references.** Can a Focus Thread retrieve context from
   an active Task Thread? Or strictly isolated, sharing only via memory?

6. **Spec structure.** This document covers the interaction model holistically.
   The final spec structure (whether this becomes Spec 03, gets folded into
   Spec 01, or splits across multiple specs) is TBD.

7. **Kit trial run failure.** If a Kit's trial run fails or the user rejects
   the result, what happens? Retry? Kit automation stays disabled until user
   manually re-triggers?

8. **Kit auto-trust threshold.** What value of N for "N successful runs before
   auto-trust upgrade"? Fixed? Per-risk-level? Configurable?
