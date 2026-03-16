# Config Overhaul Plan

## Goal
Multi-provider, profiles, thinking config, YAML-based. (Completed — RuntimeConfig eliminated, DotiConfig is the single source of truth.)

## Phase 1: Config Models (backend)
**Files**: `backend/app/core/config/models.py` (new)
- ThinkingMode enum: none, mandatory, budget
- ThinkingStyle enum: budget, level_openai
- ThinkingConfig: mode, style, default_budget, default_level
- ModelConfig: id, context_window, pricing, thinking
- ProviderConfig: api_base, api_key, models dict
- ProfileRole: model ref, thinking enabled/budget/level, context max_tokens/compression_threshold
- ProfileConfig: name, description, primary, long_context, automation
- SecurityConfig: tool_approval, tool_allowlist, sandbox_runtime
- DotiConfig: config_version, providers dict, profile, security, workspace, concurrency, etc.

## Phase 2: Config Loader (backend)
**Files**: `backend/app/core/config/loader.py` (new)
- Load from YAML (single file for now)
- Env var interpolation
- Validate model references
- Fall back to current env-based config if no YAML exists

## Phase 3: Provider Registry Refactor (backend)
**Files**: `backend/app/agent/provider_client.py`, `backend/app/api/ws/router.py`
- ProviderClient accepts resolved model config
- Router resolves model from profile -> provider -> model config

## Phase 4: Config REST API (backend)
**Files**: `backend/app/api/rest/routes.py`
- Full CRUD for providers, profiles
- GET/PATCH for all config sections

## Phase 5: Full-page Settings UI (frontend)
**Files**: `frontend/src/features/settings/SettingsPage.tsx` (new), `frontend/src/app/App.tsx`
- Route-based or state-based full page
- Sections: Providers, Profile, Security, Appearance
- Provider management: add/edit/delete providers and models
- Profile editor: select models per role, configure thinking
