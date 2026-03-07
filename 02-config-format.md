# Spec 02: Config Format

> Version: 3 | Status: Phase 1 Required | Last updated: 2026-03-07

## Overview

YAML configuration with a main entry file and optional split files via an
`include` mechanism. Supports environment variable interpolation (`${VAR}`).

Configuration is split by concern: provider/model registration, agent profiles,
security, and runtime settings. Users edit files on the host machine — they are
mounted into the Core container via Docker volume.

## File Structure

```
deploy/configs/
├── config.yaml              # Main entry: version + include list
├── providers.yaml           # Upstream LLM providers and model registration
├── profiles/
│   ├── balanced.yaml        # Agent model profile (name is arbitrary)
│   ├── budget.yaml
│   └── performance.yaml
├── security.yaml            # Authentication, tool approval, sandbox
└── runtime.yaml             # Concurrency, storage, embedding, events, automation
```

## Include Mechanism

The main config file can include other files via the `include` field:

```yaml
# config.yaml
config_version: 3
include:
  - providers.yaml
  - profiles/balanced.yaml
  - security.yaml
  - runtime.yaml
```

### Rules

- Included files are resolved relative to the main config file's directory.
- Each included file uses **full config paths** in its content. File names do
  not affect config structure — only the content inside matters.
- Files are deep-merged in `include` order. Later files override earlier ones
  on key conflicts.
- The main config file's own keys have highest priority (override all includes).
- Duplicate keys across included files at the same path cause an **error** at
  startup, unless one is the main file (which wins).
- The `include` field itself is not recursive — included files cannot include
  other files.

### Single-File Mode

Users can skip `include` and put everything in `config.yaml` directly. The
split-file layout is a convenience, not a requirement.

## Provider Configuration

Providers register upstream LLM API connections and their available models.
This is a **thin wrapper over LiteLLM** — we only configure what LiteLLM
doesn't know or where we need to override its defaults.

```yaml
# providers.yaml

providers:
  openrouter:
    api_base: "https://openrouter.ai/api/v1"
    api_key: "${OPENROUTER_API_KEY}"
    models:
      sonnet:
        id: "openrouter/anthropic/claude-sonnet-4-20250514"
        thinking:
          mode: "budget"
          style: "budget"
          default_budget: 10000

      haiku:
        id: "openrouter/anthropic/claude-haiku-4-20250514"
        thinking:
          mode: "none"

      gpt5:
        id: "openrouter/openai/gpt-5.2"
        thinking:
          mode: "budget"
          style: "level_openai"
          default_level: "medium"

  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    models:
      opus:
        id: "claude-opus-4-0-20250514"
        thinking:
          mode: "budget"
          style: "budget"
          default_budget: 16000

      sonnet:
        id: "claude-sonnet-4-20250514"
        thinking:
          mode: "budget"
          style: "budget"
          default_budget: 10000

  deepseek:
    api_base: "https://api.deepseek.com/v1"
    api_key: "${DEEPSEEK_API_KEY}"
    models:
      v3:
        id: "deepseek/deepseek-chat"
        thinking:
          mode: "none"

      r1:
        id: "deepseek/deepseek-reasoner"
        thinking:
          mode: "mandatory"

  small-reseller:
    api_base: "https://some-reseller.com/v1"
    api_key: "${RESELLER_KEY}"
    models:
      sonnet-cheap:
        id: "anthropic/claude-sonnet-4-20250514"
        context_window: 200000          # override: this reseller caps at 200K
        pricing:                         # override: different pricing
          input: 2.00
          output: 10.00
        thinking:
          mode: "budget"
          style: "budget"
          default_budget: 10000

  ollama:
    api_base: "http://localhost:11434/v1"
    models:
      llama3:
        id: "ollama/llama3"
        thinking:
          mode: "none"
```

### Provider Fields

| Field | Required | Description |
|-------|----------|-------------|
| `api_base` | No | API endpoint URL. Omit for providers LiteLLM knows natively (e.g. `anthropic`). |
| `api_key` | No | API key. Supports `${ENV_VAR}` interpolation. Omit for keyless providers (e.g. local Ollama). |
| `models` | Yes | Map of model alias → model definition. |

### Model Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `id` | Yes | — | LiteLLM model identifier. Passed directly to `litellm.completion(model=...)`. |
| `context_window` | No | LiteLLM built-in | Max context tokens. Only set to override LiteLLM's value. |
| `pricing.input` | No | LiteLLM built-in | USD per 1M input tokens. Only set for resellers or unlisted models. |
| `pricing.output` | No | LiteLLM built-in | USD per 1M output tokens. |
| `thinking` | Yes | — | Thinking/reasoning configuration. See below. |

### Alias Rules

- Provider aliases and model aliases: letters, numbers, hyphens, underscores only.
- **Slashes are forbidden** in aliases.
- System-wide model reference format: `provider_alias/model_alias` (e.g. `openrouter/sonnet`).
- The slash in the reference is the separator — this is why aliases themselves cannot contain slashes.

### Principle: Don't Declare What LiteLLM Knows

LiteLLM has built-in mappings for context windows, pricing, and provider
protocols for hundreds of models. Our provider config should only contain:

- **Always**: `id` (LiteLLM model identifier) and `thinking` config
- **Only when overriding**: `context_window`, `pricing`, `api_base`

If a field is omitted, Core queries LiteLLM for the default value at startup.

## Thinking Configuration

### Modes

| Mode | Meaning | User can toggle? | Examples |
|------|---------|------------------|---------|
| `none` | Model does not support thinking | No. `thinking.enabled: true` in profile → warning, ignored. | Haiku, DeepSeek V3, Llama3 |
| `mandatory` | Model always thinks, cannot be disabled | No. `thinking.enabled: false` in profile → warning, ignored. | DeepSeek R1, o1 |
| `budget` | Thinking can be toggled and intensity configured | Yes. | Sonnet, Opus, GPT-5.2 |

### Styles (only applies when mode = `budget`)

| Style | Parameter sent to LLM | Configured in profile via | Values |
|-------|----------------------|--------------------------|--------|
| `budget` | `thinking.budget_tokens` (Claude API) | `thinking.budget: <int>` | Token count (e.g. 10000) |
| `level_openai` | `reasoning_effort` (OpenAI API) | `thinking.level_openai: "<level>"` | `"low"` / `"medium"` / `"high"` |

### Strict Matching in Profiles

Core validates that profile thinking fields match the model's declared style:

| Model style | `thinking.budget` in profile | `thinking.level_openai` in profile |
|-------------|-----------------------------|------------------------------------|
| `budget` | Valid | Error: wrong style |
| `level_openai` | Error: wrong style | Valid |

This prevents silent misconfiguration where a user thinks they set a thinking
parameter but it has no effect.

## Agent Profiles

A profile defines which models to use for each agent role. Profile file names
are arbitrary — the `profile.name` field inside is what matters.

```yaml
# profiles/balanced.yaml

profile:
  name: "balanced"
  description: "Daily driver — good balance of quality and cost"

  primary:
    model: "anthropic/sonnet"
    thinking:
      enabled: true
      budget: 12000
    context:
      max_tokens: 200000
      compression_threshold: 0.6

  long_context:
    model: "openrouter/haiku"
    thinking:
      enabled: false
    context:
      max_tokens: 200000

  automation:
    model: "openrouter/gpt5"
    thinking:
      enabled: true
      level_openai: "low"
    context:
      max_tokens: 128000
```

### Model Roles

| Role | Purpose | Characteristics |
|------|---------|----------------|
| `primary` | Handles direct user conversation. Receives `chat.send` messages. | Best reasoning, instruction following, "EQ". |
| `long_context` | Compresses context when primary hits `compression_threshold`. Not a separate agent — works transparently behind primary. | Cheap, large context window, good summarization. |
| `automation` | Executes Automation Runs when a Subscription is triggered. Reads Routines and calls MCP tools. | Good tool use, cheap (high token volume from tool calls). |

### Agent Execution Flow

```
User message → Primary Model
                 ├── Needs tools → Primary calls MCP tools directly
                 ├── Context full → Long Context Model compresses
                 │                  → Primary continues with compressed context
                 └── Direct reply → User

Trigger event → Subscription matches → Automation Model
                 ├── Reads Routine instructions
                 ├── Calls MCP tools from any Skill
                 └── Reports results to Main
```

### Context Override

`context.max_tokens` in a profile **overrides** the model's `context_window`
from providers.yaml. This allows cost control (e.g. staying within a cheaper
pricing tier by limiting to 200K on a 1M-capable model).

If `context.max_tokens` exceeds the model's `context_window`, Core clamps it
and logs a warning.

## Security Configuration

```yaml
# security.yaml

security:
  api_token: null                     # [reload] required — auto-generated on first `doti up`
  tool_approval: "ask_first"          # [reload] ask_first | auto | auto_with_allowlist
  tool_allowlist: []                  # [reload] Tool names for auto_with_allowlist
  sandbox_runtime: "subprocess"       # [static] subprocess | docker
```

## Runtime Configuration

```yaml
# runtime.yaml

concurrency:                          # [reload]
  max_parallel_sessions: 5
  resource_acquire_timeout: 60        # seconds

storage:                              # [static]
  database_url: "sqlite+aiosqlite:///data/doti.db"

workspace:                            # [reload]
  path: "./workspace"                 # workspace root directory

memory:                               # [reload]
  embedding:
    model: "openai/embed-small"       # references providers.yaml alias
    # Changing embedding model invalidates all stored vectors.
    # Core will warn and require confirmation before re-indexing.

automation:                           # [reload]
  triggers: "workspace/triggers.json" # trigger definitions file
  subscriptions: "workspace/subscriptions.json"  # subscription rules file
  routines_dir: "workspace/routines"  # directory containing Routine markdown files
  event_retention_days: 7             # how long to keep events in the queue
  run_retention_days: 30              # how long to keep Automation Run records

events:                               # [live]
  injection:
    default: false
    rules: []                         # see Spec 06 for rule format
```

## Config Mutability Levels

Every config field belongs to one of three levels, annotated in brackets above.

| Level | Meaning | How to apply |
|-------|---------|-------------|
| **static** | Read at startup only. Requires container restart. | `doti down && doti up` |
| **reload** | Applied on config re-read. No restart needed. | `doti config reload` or `POST /api/v1/config/reload` |
| **live** | Changed via API, immediate effect, persisted to file. | `doti config set` or `config.set` via WebSocket |

### Static Fields

| Field | Reason |
|-------|--------|
| `storage.database_url` | Database connection established at startup |
| `security.sandbox_runtime` | Sandbox environment initialized at startup |

All other fields are `reload` or `live`.

### Reload Behavior (`POST /api/v1/config/reload`)

1. Core re-reads all config files from disk (main + includes)
2. Validates all fields
3. Applies `reload` and `live` level changes immediately
4. Returns: `applied` (changed fields), `restart_required` (static fields that
   changed), `errors` (validation failures)

### Set Behavior (`config.set` / `doti config set`)

1. Validates the new value
2. Applies immediately if `live` or `reload`
3. Writes change back to the **correct split file** (Core tracks which file
   each key originated from)
4. If `static`, returns `config_restart_required` and writes to file only

## Environment Variable Interpolation

Any string value can use `${VAR_NAME}`. Resolved at config load time. Missing
variables → warning + empty string.

The `.env` file in the project root is loaded by Docker Compose:

```
# .env
DOTI_LLM_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Unknown Fields and Validation

| Condition | Behavior |
|-----------|----------|
| Unknown field under a known section (e.g. `security.foo`) | **Warning** logged, field ignored. Catches typos. |
| Unknown top-level section | Silently ignored. Allows user-defined metadata. |
| Known field with invalid value | **Error**. Startup aborted or reload rejected. |
| Missing required field (e.g. `security.api_token`) | **Error**. Startup aborted. |
| Missing optional field | Default value applied silently. |

## Startup Validation Sequence

1. Read `config.yaml` and resolve all `include` files
2. Merge and validate against schema
3. Resolve `${ENV_VAR}` references
4. Load `providers` → for each model, query LiteLLM for defaults, apply overrides
5. **Model health check**: ping each registered provider/model endpoint
6. Load active `profile` → validate all model references exist and are healthy
7. Validate thinking field compatibility (style matching)
8. Validate context overrides (clamp if exceeding model's context_window)
9. Load remaining config sections (security, runtime, automation)
10. Start Core services

## Forward Compatibility

- New fields always get sensible defaults
- Structural changes bump `config_version`
- Core reads `config_version` and applies migration if needed (e.g. renaming
  fields when upgrading across versions)
- Old config versions are auto-migrated with a logged warning

## Type Definitions

See `packages/shared/doti_shared/models/config.py`
