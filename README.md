<div align="center">

# ./doti

**A tiny dot that works for you.**

Safety-first AI agent platform. Runs on your machine. Follows your rules.

A [Dotislash](https://github.com/dotislash) project.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)

</div>

---

## What is DOTI?

DOTI is an open-source AI agent platform built around one principle: **your agent should ask before it acts**.

Every tool declares its risk level. Every action flows through an approval gate. Shell commands only execute inside sandboxed containers. Your data stays on your machine.

DOTI connects to your LLM provider of choice via [LiteLLM](https://docs.litellm.ai/) and uses [MCP](https://modelcontextprotocol.io/) (Model Context Protocol) for extensible tool integration.

### Two Deployment Modes

**Client mode** — A smart MCP client with a Web UI. Connect tools and Skills, chat with your agent, approve actions. No always-on process needed.

**Server mode** — Always-on event bus, automation triggers, multi-executor orchestration. Your agent watches for events and acts proactively.

### Safety Architecture

```
Main Agent (safe)
├── read_file    (low risk)     — reads workspace files
├── write_file   (medium risk)  — writes workspace files
├── list_directory (low risk)   — lists directory contents
└── executor_run (high risk)    — delegates to Docker sandbox
       ↓
   Executor Container (isolated)
   └── shell commands run here, not in main agent
```

The main agent has **zero shell access**. All destructive operations happen inside Docker Executor containers. The agent can target multiple executors without per-machine tool declarations.

### Skills

A Skill is an installable package with instructions (markdown) and optional MCP servers/scripts. Skills answer "what tools exist" and "how to use them for complex tasks."

### Automation (Server Mode)

Event-driven system with four components:

```
Trigger (background)  →  Event Queue  →  Subscription matches  →  Routine executes
```

**Triggers**: Interval timer, cron schedule, file watcher.
**Routines**: Markdown instruction files that tell the agent what to do.

Automation is off by default — enable it in config when needed.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- An LLM API key (OpenRouter, Anthropic, OpenAI, etc.)
- Docker (optional — for Executor sandboxes)

### Quick Start

```bash
git clone https://github.com/dotislash/doti.git
cd doti

# Backend
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` to use the Web UI.

### Configuration

DOTI uses a single YAML config file. On first run, it falls back to environment variables.

```yaml
# config.yaml
config_version: 3

providers:
  anthropic:
    api_key: "${DOTI_API_KEY}"
    models:
      sonnet:
        id: "anthropic/claude-sonnet-4-5"

profile:
  primary:
    model: "anthropic/sonnet"

security:
  tool_approval: "ask_first"    # ask_first | auto | auto_with_allowlist
```

Or use environment variables only:

```bash
export DOTI_API_KEY=your-key
export DOTI_MODEL=anthropic/claude-sonnet-4-5
uvicorn app.main:app
```

Config changes via REST API are persisted back to `config.yaml`.

## Architecture

### Project Structure

```
doti/
├── backend/
│   └── app/
│       ├── agent/          # Conversation manager, provider client, runtime (agent loop)
│       ├── api/            # WebSocket handlers + REST endpoints
│       ├── automation/     # Event queue, triggers, routines (toggleable)
│       ├── core/           # Config, models, audit logging
│       ├── executor/       # Docker container management + shell tool
│       ├── memory/         # MEMORY.md + HISTORY.md + context builder
│       ├── storage/        # JSONL persistence (messages, threads)
│       └── tools/          # Tool base, registry, filesystem tools, executor tool
├── frontend/
│   └── src/
│       ├── features/       # Chat, sidebar, settings components
│       ├── lib/            # WebSocket client, utilities
│       └── state/          # Zustand stores
└── plans/                  # Implementation plans
```

### Key Design Decisions

**Code is the spec.** Protocol envelopes are Pydantic models. Config schema is a Pydantic model. Risk levels are an enum. These are executable specifications that can't drift from the implementation.

**Everything is MCP.** Built-in tools and external integrations all speak the same protocol.

**Memory is LLM-driven.** When conversations exceed a threshold, the agent itself summarizes old messages into `MEMORY.md` (long-term facts) and `HISTORY.md` (searchable log). No rule-based extraction.

**Executors are the hands.** The main agent is the brain — it thinks, plans, reads. Executors are the hands — they run shell commands in isolated Docker containers. One agent, many executors, clean separation.

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Frontend | React 19, TypeScript, Vite, Zustand, Tailwind |
| LLM | LiteLLM (100+ providers) |
| Storage | JSONL (append-only) |
| Sandboxing | Docker (for Executor containers) |

### Project Status

> **DOTI is in active development.** Core architecture is implemented and usable. Expect breaking changes.

| Area | Status |
|------|--------|
| Agent loop (ReAct, streaming, tool calls) | Done |
| WebSocket protocol (typed envelopes) | Done |
| Tool approval (risk levels, approval gates) | Done |
| Filesystem tools (read, write, list) | Done |
| Executor tool (Docker sandbox) | Done |
| Memory system (MEMORY.md + HISTORY.md + LLM consolidation) | Done |
| Config system (YAML + env, runtime persistence) | Done |
| Automation (event queue, triggers, routines) | Framework done, toggleable |
| Skills system | Planned |
| MCP server integration | Planned |
| Multi-executor orchestration | Planned |

## Contributing

DOTI is in active development. Contributions welcome.

The codebase is the source of truth — there are no external spec documents. Read the code, especially `backend/app/api/ws/protocol.py` (protocol envelopes) and `backend/app/core/config/models.py` (config schema).

### Development Setup

```bash
git clone https://github.com/dotislash/doti.git
cd doti/backend
pip install -e ".[dev]"
pytest                     # Run tests
uvicorn app.main:app --reload
```

## License

DOTI is licensed under the [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0-only).

Freely use, modify, and distribute — but derivative works (including network/SaaS use) must also be open-sourced under AGPL-3.0.
