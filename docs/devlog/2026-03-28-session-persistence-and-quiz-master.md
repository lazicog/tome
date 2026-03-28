# 2026-03-28: Session Persistence & Quiz Master Agent

## What was done

### Storage provider swap
- Created `backend/app/services/storage_provider.py` that delegates to JSON or SQLite based on `use_sqlite_storage` config flag
- Updated `books.py` and `chat.py` route imports to use the provider layer
- Created `backend/app/services/migrate.py` for one-shot JSON-to-SQLite migration

### Session-aware chat
- Chat route now creates a session and persists user/assistant messages when SQLite is enabled
- Emits `session` SSE event with the session ID so frontend can track it
- Session resume: passing `session_id` in chat request loads history from DB instead of client-provided `chat_history`
- Added `session_id` optional field to `ChatRequest` schema

### Session API endpoints
- `GET /api/sessions/book/{book_id}` -- list sessions with message counts
- `GET /api/sessions/{session_id}/messages` -- retrieve full message history
- New schemas: `SessionResponse`, `SessionMessagesResponse`
- Sessions router registered in `main.py`

### Frontend session sidebar
- Chat page now shows a sessions sidebar listing past conversations per book
- Click a session to resume it (loads history from API)
- "+ New" button to start fresh conversations
- Enter key support for sending messages
- Empty state messages for new users
- Home page updated from "Phase 1" branding to current "Tome" with updated tagline

### Quiz Master agent
- Spec: `docs/specs/2026-03-28-quiz-master-agent.md`
- Added `QUIZ_PROMPT` in `backend/app/agents/quiz_master.py`
  - Generates 3-5 mixed question types (multiple-choice, true/false, short-answer) from RAG context
- Extended router with `quiz` intent keywords
- Added `quiz_prep` node to LangGraph graph
- Frontend displays "Quiz Master" label for quiz agent responses
- Router now classifies: `context` > `quiz` > `example` > `explain` (fallback)

### Test coverage expansion
- 5 new session chat integration tests (session creation, resume, list, messages, 404)
- 5 new quiz router classification tests
- 1 new quiz SSE stream integration test
- Total: **46 tests, all passing**

## Key decisions made

- Storage provider pattern (thin re-export) avoids touching test mocks that reference `storage.py` directly
- Session persistence is gated behind `use_sqlite_storage` flag so existing JSON flow works unchanged
- Quiz intent classification uses keyword matching consistent with existing router pattern
- Context terms take priority over quiz terms in classification order to avoid misrouting

## Issues / Gotchas

- `asyncio.get_event_loop().run_until_complete()` in sync integration tests triggers a deprecation warning; acceptable for now since these are test-only patterns

## Next steps

- Enable `use_sqlite_storage=True` by default once migration helper is validated
- Add quiz answer evaluation flow (user answers -> Quiz Master grades)
- Plan Study Planner agent for structured learning paths
- Consider learning progress tables for tracking mastery over time
