# DOTI Shell Security Execution Plan

> Version: v1.0 | Author: Sam | Date: 2026-03-09

## Architecture

```
User Command → Layer 0 (Parse) → Layer 1 (Whitelist) → Layer 2 (AI Review, optional) → Layer 3 (Sandbox Execution)
```

## Roadmap
- v1.0 (P0): Layer 0 + Layer 1 + Basic executor (current sprint)
- v1.1 (P1): Layer 2 AI review
- v1.2 (P1): Linux bwrap native sandbox
- v2.0 (P2): Docker sandbox + custom image + network policy
- v2.1 (P2): Windows Job Object / macOS sandbox-exec
- v2.2 (P2): Role-based permissions + audit dashboard

## Implementation Scope (v1.0)

Files to create/modify:
- `backend/app/tools/builtins/shell_policy.py` — ParsedCommand, whitelist engine, path validation
- `backend/app/tools/builtins/shell.py` — Integrate policy check before execution
- `backend/app/core/config/models.py` — ShellConfig model
- `backend/tests/test_shell_policy.py` — Whitelist + path validation tests

See full design doc in user's message for detailed Layer specs.
