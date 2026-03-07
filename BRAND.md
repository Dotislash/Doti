# Dotislash Brand Guide

## The Name

**Dotislash** — written as one word, capitalized at the start of sentences, lowercase elsewhere.

It breaks down into three parts: **DOT**, **I**, and **SLASH**.

The symbol `./` is the brand mark.

## Mission

> Harness the power of AI to universally enhance individual capabilities.

We build tools that put AI in the hands of individuals — running on their hardware, under their control, augmenting what they can do.

## The Symbol: `./`

In a terminal, `./` means "execute something right here, right now." That's the spirit of Dotislash: agency starts where you are.

The dot and the slash carry layered meanings, intentionally left open:

- **Command-line roots.** `./` is how you run a program in the current directory. It's local, direct, personal.
- **Dot as the individual.** A single point — you, your device, your data. Small but present.
- **Slash as the tool.** The path forward, the action, the AI that extends what the dot can do.
- **Together.** `./` is the moment where a person and a tool meet. Execute. Right here.

We don't enforce a single interpretation. The ambiguity is deliberate — it invites curiosity and leaves room for the brand to grow.

## Projects

| Project | Description | Status |
|---------|-------------|--------|
| **./doti** | Self-hosted AI agent platform | Active development |

## Key Concepts

### Skills

A **Skill** is DOTI's installable package for capabilities and knowledge. It bundles instructions (markdown files telling the agent how to perform complex tasks) with optional MCP servers or scripts that provide specialized tools.

Skills are the primary way users extend their agent's interactive capabilities. Installing a Skill gives the agent new tools and the knowledge of how to use them for complex tasks.

Under the hood, every Skill's tools are standard [MCP](https://modelcontextprotocol.io/) servers — the same protocol used by Claude, Cursor, and a growing ecosystem of AI tools. Any existing MCP server can be wrapped into a Skill with zero changes. DOTI adds instructions and a permission layer on top.

### Automation

**Automation** is DOTI's event-driven system for proactive agent behavior. It consists of four decoupled components:

- **Triggers** — background scripts that produce events (cron schedules, file watchers, webhooks)
- **Event Queue** — central bus that collects all trigger events
- **Subscriptions** — rules that filter events and wake the agent
- **Routines** — markdown instructions the agent follows when woken up

Automation is deliberately separate from Skills. A Routine can use tools from any installed Skill, and permissions are inherited from each tool's declared risk level — not from the Skill or Automation package.

## Usage Guidelines

### Project naming

Dotislash projects use the `./` prefix in display names:

- `./doti` — not "DOTI" or "Doti" in titles
- In running text, "DOTI" (uppercase) or "doti" (lowercase) are both acceptable
- CLI commands use `doti` (no prefix)

### The `./` mark

- Always rendered in monospace when possible: `./`
- In contexts where monospace isn't available, use plain text: ./
- Don't add spaces: `./doti`, not `. / doti`

### Organization references

- Full name: **Dotislash**
- GitHub: `@dotislash`
- In casual context: "dotislash" (lowercase) is fine

## Origin

Dotislash was founded as a student initiative exploring AI-powered tools for individual productivity. The name and symbol were chosen to reflect a belief that AI should be personal, local, and immediate — something you invoke yourself, not something that runs in someone else's cloud.

The organization's focus has evolved from workflow-based agents to general-purpose, self-hosted AI — but the core conviction remains: **the dot is you, and the slash is what you can do next.**
