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

DOTI is an open-source, self-hosted AI agent platform. It connects to your LLM provider of choice, uses [MCP](https://modelcontextprotocol.io/) (Model Context Protocol) for tool integration, and introduces **Kits** — installable packages that give your agent both the ability to act *and* the awareness to act on its own.

You deploy it with Docker. You control it with a cross-platform CLI or Web UI. Every action can require your explicit approval. Your data stays on your hardware.

**Your AI should live in your house, not someone else's.** Every major AI product today asks for your data and runs on their servers. DOTI flips that — your agent runs on your machine, talks to your devices, follows your rules.

**One dot connects everything.** Your phone, laptop, NAS, calendar, codebase — DOTI treats each connected device as another dot in the network. They all speak the same protocol, and the agent orchestrates them.

**AI should raise its hand before it acts.** Every Kit declares what it needs. Every action can require your approval. Everything is logged. Capable, but it asks first.

### Kits

A Kit is an installable package that gives your agent new capabilities. It can contain **tools** (things the agent can do when you ask), **triggers** (events that wake the agent up on their own), or both.

For example, a Calendar Kit gives your agent the ability to check your schedule when you ask — but also wakes it up every morning at 8 AM to brief you on today's meetings. One install, both directions.

**Tool Kit** — gives the agent new abilities, but only when you ask. A file operations Kit lets the agent read and write files in your workspace. It never acts on its own.

**Trigger Kit** — wakes the agent up when something happens, but doesn't add new tools. A morning briefing Kit fires every day at 8 AM with the prompt "summarize my day", using whatever other Kits are already installed.

**Full Kit** — both. An email Kit lets the agent search your inbox and draft replies when you ask, *and* alerts you when an important message arrives.

#### Kits vs. Skills

Most AI agent frameworks use "Skills" or "Plugins" — packages that give an agent new tools to call. Kits include that, but go further. A Skill is **passive**: it waits for the agent to call it. A Kit can be **active**: it watches for events and wakes the agent up with a task. This means things that would normally require a separate automation system (cron jobs, webhook handlers, sensor monitors) are bundled right into the same package that provides the tools. No separate config, no separate system — one Kit, complete loop.

Under the hood, every Kit's tools are standard [MCP](https://modelcontextprotocol.io/) servers — the same protocol used by Claude, Cursor, and a growing ecosystem of AI tools. Any existing MCP server can be wrapped into a Kit with zero changes. DOTI adds a permission layer, event triggers, and agent instructions on top.

### Other Concepts

```
You
 ├── doti CLI (host)       Control plane: manage, configure, update
 └── Web UI (:3000)        Chat, approvals, monitoring
      ↕ WebSocket
DOTI Core (Docker)          Agent loop, LLM, permissions, event bus
      ↕ MCP Protocol                          ↑ Events
 ┌──────────────────────────────────────────────┐
 │  Kits                                        │
 │                                              │
 │  Tools (agent calls out)                     │
 │  calendar · email · files · web-search       │
 │                                              │
 │  Triggers (world calls in)                   │
 │  cron · webhook · device sensor · threshold  │
 └──────────────────────────────────────────────┘
```

**Core** — The brain. Runs inside Docker. Manages your LLM, chat sessions, Kit permissions, and routes tool calls. You never need to enter the container — the CLI and Web UI handle everything from outside.

**Nodes** — Your devices, connected to Core via a lightweight agent. A Node exposes its device capabilities (shell, filesystem, clipboard, sensors) as a set of Kits through a reverse WebSocket tunnel. Your desktop becomes a collection of tools and sensors that the agent can use — with your permission.

**Swarms** — Multiple agents collaborating on a task through shared context and an event bus. *(Planned — not yet available.)*

### Project Status

> **DOTI is in early development (alpha).** The architecture and specs are defined, core scaffolding is in place, but many features are still being implemented. Expect breaking changes.

What works today: project scaffolding, monorepo structure, versioned spec definitions, database schema with migrations, WebSocket and REST API scaffolding, Docker Compose deployment, and a Web UI shell.

| Phase | Focus | Status |
|-------|-------|--------|
| **1 — Foundation** | Docker deployment, MCP broker, agent loop with tool calling, streaming chat | 🔨 In progress |
| **2 — Control & Config** | Host CLI (`doti` command), config hot-reload, event bus | 📋 Spec'd |
| **3 — Memory & Automation** | Context compression, long-term memory, Kit triggers (cron, webhook) | 📋 Spec'd |
| **4 — Device Network** | Node agent, reverse tunnel, device pairing | 📐 Designed |
| **5 — Multi-Agent** | Swarm mode, shared context, agent collaboration | 📐 Designed |

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
  kit_approval: "ask_first"   # ask_first | auto | auto_with_allowlist
```

Some settings take effect immediately, others require a restart. See [Configuration Reference](docs/configuration.md) for the full list.

### Host CLI *(coming in Phase 2)*

```bash
pipx install doti-cli

doti up / down / logs             # Manage the Docker deployment
doti status                       # Health check
doti config edit / get / set      # Configuration management
doti kit list / install / enable  # Kit management
doti node list / pair             # Device management (Phase 4)
doti update                       # Pull latest images and restart
doti backup                       # Back up database and config
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

**Spec-first.** Every interface is a versioned specification defined before code is written. Protocol messages carry version numbers. Schemas are migration-managed. Config files declare their format version. Internals can evolve without breaking your data, Kits, or connected devices.

**Everything is MCP.** Built-in tools, third-party integrations, and remote devices all expose capabilities through the Model Context Protocol. The Core doesn't distinguish between a local file reader and a remote desktop — they're both MCP servers with different transports.

**MCP + Events.** MCP handles the downward path (agent calls tools). A lightweight event bus handles the upward path (triggers and devices push events to the agent). Two directions, unified in one package: the Kit.

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
| [Writing Kits](docs/writing-kits.md) | How to create DOTI Kits (MCP + triggers) |
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
