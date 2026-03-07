<div align="center">

# ./doti

**A tiny dot that works for you.**

Self-hosted AI agent with tool use, device control, and scheduled automation.
Runs on your machine. Follows your rules.

A [Dotislash](https://github.com/dotislash) project.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)

[What is DOTI?](#what-is-doti) · [Getting Started](#getting-started) · [Architecture](#architecture) · [Contributing](#contributing)

</div>

---

## What is DOTI?

DOTI is an open-source, self-hosted AI agent platform. It connects to your LLM provider of choice, uses [MCP](https://modelcontextprotocol.io/) (Model Context Protocol) for tool integration, and provides a three-layer architecture — **MCP** for execution, **Skills** for knowledge, and **Automation** for event-driven proactive behavior.

You deploy it with Docker. You control it with a cross-platform CLI or Web UI. Every action can require your explicit approval. Your data stays on your hardware.

**Your AI should live in your house, not someone else's.** Every major AI product today asks for your data and runs on their servers. DOTI flips that — your agent runs on your machine, talks to your devices, follows your rules.

**One dot connects everything.** Your phone, laptop, NAS, calendar, codebase — DOTI treats each connected device as another dot in the network. They all speak the same protocol, and the agent orchestrates them.

**AI should raise its hand before it acts.** Every tool declares its risk level. Every action can require your approval. Everything is logged. Capable, but it asks first.

### Skills

A Skill is an installable package that gives your agent new capabilities and knowledge. It contains **instructions** (markdown files telling the agent how to perform complex tasks) and can optionally bundle **MCP servers** or **scripts** that provide specialized tools.

For example, an Email Skill gives your agent instructions on how to triage your inbox, plus an MCP server that provides `email.list`, `email.send`, and `email.archive` tools. When you ask "help me clean up my inbox," the agent loads the Skill's instructions and uses its tools.

Skills are the knowledge layer — they answer "what tools exist" and "how to use them for complex tasks."

### Automation

Automation is a separate, event-driven system that lets your agent act proactively without user interaction. It consists of four components:

**Triggers** — Background scripts that run continuously and push events into a central queue. A cron trigger fires every morning at 8 AM. A file-watch trigger fires when a file changes. Triggers only produce events — they don't know or care who consumes them.

**Event Queue** — A central bus that collects all trigger events. Every event has a type, source, and payload. The queue is persistent and inspectable.

**Subscriptions** — Rules that filter the event queue and wake up the agent. "When `cron.fired` from `morning-check` appears, load this Routine." Subscriptions bind triggers to actions without either side knowing about the other.

**Routines** — Markdown instruction files that tell the agent what to do when woken up by a subscription. The agent reads the Routine, uses whatever MCP tools it needs (from any installed Skill), and reports results.

```
Trigger (background)
  → pushes event to Event Queue
    → Subscription matches event
      → Agent wakes up in a dedicated Thread
        → Reads Routine instructions
          → Uses MCP tools from any Skill to execute
            → Reports results to Main
```

#### Why separate Skills and Automation?

Most AI agent frameworks bundle tools and automation triggers into one package ("plugins" or "kits"). This creates a fundamental problem: if an automation needs tools from multiple packages, permissions get tangled. Which package "owns" the automation? How do you scope permissions across package boundaries?

DOTI separates them cleanly:

- **Skills** define what tools exist (capabilities)
- **Automation** defines when and how to use them (orchestration)

An Automation can reference tools from any installed Skill. Permission is inherited from each tool's declared risk level — not from the Skill or Automation package. This means cross-Skill automations work naturally without permission conflicts.

### Other Concepts

```
You
 ├── doti CLI (host)       Control plane: manage, configure, update
 └── Web UI (:3000)        Chat, approvals, monitoring
      ↕ WebSocket
DOTI Core (Docker)          Agent loop, LLM, permissions, event bus
      ↕ MCP Protocol                       ↑ Events
 ┌──────────────────────────────────────────┐
 │  Skills (knowledge + tools)              │
 │  email · calendar · filesystem · web     │
 │                                          │
 │  Automation (event-driven)               │
 │  Triggers → Event Queue → Subscriptions  │
 │  cron · webhook · file-watch · threshold │
 │  → Routines (what to do when triggered)  │
 └──────────────────────────────────────────┘
```

**Core** — The brain. Runs inside Docker. Manages your LLM, chat sessions, tool permissions, and routes tool calls. You never need to enter the container — the CLI and Web UI handle everything from outside.

**Nodes** — Your devices, connected to Core via a lightweight agent. A Node exposes its device capabilities (shell, filesystem, clipboard, sensors) as a set of MCP tools through a reverse WebSocket tunnel. Your desktop becomes a collection of tools and sensors that the agent can use — with your permission.

**Swarms** — Multiple agents collaborating on a task through shared context and an event bus. *(Planned — not yet available.)*

### Project Status

> **DOTI is in early development (alpha).** The architecture and specs are defined, core scaffolding is in place, but many features are still being implemented. Expect breaking changes.

What works today: project scaffolding, monorepo structure, versioned spec definitions, database schema with migrations, WebSocket and REST API scaffolding, Docker Compose deployment, and a Web UI shell.

| Phase | Focus | Status |
|-------|-------|--------|
| **1 — Foundation** | Docker deployment, MCP broker, agent loop with tool calling, streaming chat | In progress |
| **2 — Control & Config** | Host CLI (`doti` command), config hot-reload, event bus | Spec'd |
| **3 — Memory & Automation** | Context compression, long-term memory, Triggers, Event Queue, Subscriptions, Routines | Spec'd |
| **4 — Device Network** | Node agent, reverse tunnel, device pairing | Designed |
| **5 — Multi-Agent** | Swarm mode, shared context, agent collaboration | Designed |

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose (included with Docker Desktop)
- An LLM API key — [OpenRouter](https://openrouter.ai/) recommended for multi-model access

Works on **Windows**, **macOS**, and **Linux**. No WSL required on Windows.

### Quick Start

**1. Clone and configure:**

```bash
git clone https://github.com/dotislash/doti.git
cd doti
cp deploy/configs/config.example.yaml deploy/configs/config.yaml
```

**2. Set your API key.** Open `deploy/configs/config.yaml` and add your key, or create a `.env` file:

```
# .env (in project root)
DOTI_LLM_API_KEY=your-api-key-here
```

**3. Launch:**

```bash
docker compose up -d
```

**4. Open** `http://localhost:3000` — you'll see the DOTI chat interface. Try asking your agent a question to get started.

### Configuration

DOTI uses a single YAML config file mounted into the container from your host machine. You edit it on your host — no need to enter the container.

```yaml
# deploy/configs/config.yaml
config_version: 1

llm:
  provider: "openrouter"
  model: "anthropic/claude-sonnet-4-20250514"
  api_key: "${DOTI_LLM_API_KEY}"

  context:
    max_tokens: 128000
    compression_threshold: 0.6

security:
  tool_approval: "ask_first"   # ask_first | auto | auto_with_allowlist
```

Some settings take effect immediately, others require a restart. See [Configuration Reference](docs/configuration.md) for the full list.

### Host CLI *(coming in Phase 2)*

```bash
pipx install doti-cli

doti up / down / logs                # Manage the Docker deployment
doti status                          # Health check
doti config edit / get / set         # Configuration management
doti skill list / install / enable   # Skill management
doti automation list / enable        # Automation management
doti node list / pair                # Device management (Phase 4)
doti update                         # Pull latest images and restart
doti backup                         # Back up database and config
```

## Architecture

### Monorepo Structure

```
doti/
├── packages/
│   ├── shared/          # Pydantic models — source of truth for all specs
│   ├── core/            # FastAPI server, agent loop, MCP client, event bus
│   ├── cli/             # Host CLI (doti command)
│   ├── node/            # Lightweight device agent (desktop/server)
│   └── web/             # React + TypeScript UI
├── deploy/              # Docker Compose files, config templates, .env
├── docs/specs/          # Versioned protocol and schema specifications
└── scripts/             # Development tooling
```

### Deployment Model

```
Host machine
├── doti CLI (pipx install)       Talks to Core API + Docker
├── deploy/configs/config.yaml    Config lives on host, mounted into container
├── data/doti.db                  Data lives on host, mounted into container
└── Docker
    ├── doti-core                 Python: FastAPI, agent loop, MCP client
    └── doti-web                  React UI served by nginx

User devices
└── doti-node (pipx install)      Connects to Core via reverse WebSocket tunnel
```

### Design Principles

**Spec-first.** Every interface is a versioned specification defined before code is written. Protocol messages carry version numbers. Schemas are migration-managed. Config files declare their format version. Internals can evolve without breaking your data, Skills, or connected devices.

**Everything is MCP.** Built-in tools, third-party integrations, and remote devices all expose capabilities through the Model Context Protocol. The Core doesn't distinguish between a local file reader and a remote desktop — they're both MCP servers with different transports.

**MCP + Events.** MCP handles the downward path (agent calls tools). A lightweight event bus handles the upward path (triggers push events to the agent). Two directions, unified through Skills (tools) and Automation (events).

**Concurrency without global locks.** Multiple sessions run in parallel. Resource conflicts are resolved per-resource (file locks, shell locks), not by blocking entire sessions. The agent is told when a resource is busy and can decide to wait or do something else.

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Core | Python 3.12+, FastAPI, SQLAlchemy |
| Web UI | React 19, TypeScript, Vite, Zustand, Tailwind |
| Host CLI | Python, Click, Docker SDK |
| Node Agent | Python, MCP SDK, websockets |
| LLM Layer | LiteLLM (100+ providers behind one interface) |
| MCP | Official Python SDK |
| Database | SQLite + Alembic (migration-safe) |
| Packaging | uv workspace mode |
| Deployment | Docker Compose |

### Documentation

| Doc | Description |
|-----|-------------|
| [Specifications](docs/specs/) | Protocol definitions, schema reference, design rationale |
| [Configuration Reference](docs/configuration.md) | All config options with hot-reload annotations |
| [Writing Skills](docs/writing-skills.md) | How to create DOTI Skills (MCP + instructions) |
| [Automation Guide](docs/automation.md) | How to set up Triggers, Subscriptions, and Routines |
| [Connecting Nodes](docs/nodes.md) | Set up device agents (Phase 4) |
| [API Reference](docs/api.md) | Core API for client and CLI developers |

## Contributing

DOTI is in early development. Contributions are welcome — here's how to get started.

**Before making architectural changes**, please read the specs in `docs/specs/`. We've invested significant effort in interface stability, and changes to specs need discussion first (open an issue).

**Good first contributions**: implementing TODO items in the codebase, improving test coverage, documentation, and cross-platform testing.

### Development Setup

```bash
git clone https://github.com/dotislash/doti.git
cd doti
uv sync                    # Install all workspace dependencies
```

Start Core and Web in development mode with hot reload:

```bash
# Linux / macOS
./scripts/dev.sh

# Windows (PowerShell)
# Cross-platform dev runner coming soon — for now, see scripts/dev.sh
# and run the equivalent commands manually, or use WSL.
```

## License

DOTI is licensed under the [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0-only).

This means you can freely use, modify, and distribute DOTI — but any derivative work (including network/SaaS use) must also be open-sourced under AGPL-3.0. If your use case requires closed-source distribution, contact [samshuawashtaken@dotislash.com](mailto:samshuawashtaken@dotislash.com) for a commercial license.
