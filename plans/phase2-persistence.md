# Phase 2A: Main Message Persistence & History Recovery

## Goal
Make Main conversation survive server restarts. Messages persist to JSONL files.
On WS reconnect, server sends recent message history to client.

## Sub-tasks

### 2A.1 — MessageStore (JSONL persistence layer)
**Files:** `backend/app/storage/message_store.py`
- Append-only JSONL file: one JSON object per line
- Store path: `{workspace}/data/main.jsonl`
- Methods: `append(msg)`, `load_recent(n)`, `load_all()`
- Each line: `{"id": "msg_...", "role": "user"|"assistant", "content": "...", "ts": 1234567890}`
- Thread-safe (asyncio file writes)

### 2A.2 — Integrate MessageStore into ConversationManager
**Files:** `backend/app/agent/conversation.py`
- ConversationManager accepts optional MessageStore
- On add_user_message / add_assistant_message → also persist to store
- On init, load recent messages from store to populate in-memory history
- Keep MAX_HISTORY trim for LLM context, but store keeps everything

### 2A.3 — REST endpoint for message history
**Files:** `backend/app/api/rest/routes.py`, `backend/app/main.py`
- `GET /api/v1/main/messages?limit=50&before=msg_id` → paginated history
- Returns messages in reverse chronological order
- Wire into FastAPI app

### 2A.4 — WS reconnect: send history
**Files:** `backend/app/api/ws/router.py`, `backend/app/api/ws/protocol.py`
- New envelope: `history.sync` with payload `{messages: [...], has_more: bool}`
- After server.hello, send last 50 messages as history.sync
- Client uses this to populate message list on connect

### 2A.5 — Frontend: load history on connect
**Files:** `frontend/src/lib/ws/types.ts`, `frontend/src/state/chatStore.ts`
- Handle `history.sync` message type
- Populate messages array from history (avoid duplicates)
- Show loaded history immediately on connect

## Acceptance Criteria
- [ ] Messages survive server restart
- [ ] Client sees previous messages after page refresh
- [ ] REST endpoint returns paginated history
- [ ] Tests pass for MessageStore and REST endpoint
