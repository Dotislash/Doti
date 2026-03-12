# Remaining Tasks Plan

## Task 1: Thread-Scoped Chat (Independent Conversations per Thread)

### Problem
ConversationManager only persists to MessageStore (main.jsonl). When user sends a message in a thread (conversation_id != "main"), it should use ThreadStore for persistence.

### Phase 1.1: Make ConversationManager thread-aware
- **Goal**: ConversationManager supports both Main (via MessageStore) and Thread (via ThreadStore) persistence
- **Files**: `backend/app/agent/conversation.py`
- **Changes**:
  - Accept optional `thread_store` parameter
  - In `_add_message()`, if conversation_id != "main", persist via `thread_store.append_message()`
  - In `load_history()`, if conversation_id != "main", load from `thread_store.load_thread_messages()`
- **Acceptance**: Thread messages stored in `data/threads/{thread_id}.jsonl`

### Phase 1.2: Wire router to load thread history
- **Goal**: When chat.send arrives for a thread, load its history first
- **Files**: `backend/app/api/ws/router.py`
- **Changes**:
  - Pass thread_store to ConversationManager
  - Before execute_run for a thread, call `conversations.load_history(cid)` if not already loaded
- **Acceptance**: Thread conversations are independent from Main

### Phase 1.3: Tests
- **Files**: `backend/tests/test_thread_chat.py`
- **Acceptance**: Thread chat creates separate JSONL, Main is unaffected

---

## Task 2: Tool Approval Flow

### Phase 2.1: Backend approval gate
- **Goal**: High/critical tools pause execution and wait for user approval
- **Files**: `backend/app/agent/runtime.py`, `backend/app/api/ws/router.py`
- **Changes**:
  - runtime.py: yield ToolRequestEnvelope then await an approval signal (asyncio.Event or Future)
  - router.py: Handle `tool.approve` messages, resolve the pending approval
- **Acceptance**: Run pauses until user approves/denies

### Phase 2.2: Frontend approval UI
- **Goal**: ToolRequestCard shows Approve/Deny buttons for high/critical tools
- **Files**: `frontend/src/features/chat/MessageList.tsx`, `frontend/src/state/chatStore.ts`
- **Changes**:
  - ToolRequestCard: Add Approve/Deny buttons
  - chatStore: Send `tool.approve` message on button click
- **Acceptance**: User can approve/deny tools from UI

### Phase 2.3: Tests
- **Files**: `backend/tests/test_approval.py`
- **Acceptance**: Approval flow works end-to-end

---

## Task 3: Context Compression

### Phase 3.1: Summarization service
- **Goal**: When conversation exceeds threshold, summarize older messages
- **Files**: `backend/app/agent/conversation.py`
- **Changes**:
  - When history > 30 messages, summarize oldest 20 into a single summary message
  - Use provider to generate summary
- **Acceptance**: Long conversations stay within token budget

---

## Task 4: Phase 4 — Automation System

### Phase 4.1: Event Queue
- **Files**: `backend/app/automation/event_queue.py`
- **Goal**: AsyncIO-based event queue with typed events

### Phase 4.2: Triggers
- **Files**: `backend/app/automation/triggers.py`
- **Goal**: Time-based and file-watch triggers that emit events

### Phase 4.3: Subscriptions & Routines
- **Files**: `backend/app/automation/subscriptions.py`, `backend/app/automation/routines.py`
- **Goal**: Subscribe to events, execute routines (agent runs)

### Phase 4.4: Wire into main app
- **Files**: `backend/app/main.py`, `backend/app/api/ws/router.py`
- **Goal**: Automation system starts with app lifecycle
