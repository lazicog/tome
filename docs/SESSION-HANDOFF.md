# Tome Session Handoff

Use this file as the startup context when resuming work with the agent.

## How to resume

At the start of the next session, say:

`Read docs/SESSION-HANDOFF.md and continue from there.`

## Current project status

- Project: `tome` ([https://github.com/lazicog/tome](https://github.com/lazicog/tome))
- Branch: `master`
- Workflow: solo mode direct commits to `master`

## What is completed

### Foundation and conventions

- Cursor rules and skills are set up
- Spec-first workflow configured
- Documentation system active: ADRs, devlog, changelog

### Phase 1 (scaffold + hardening) - COMPLETE

- FastAPI backend with health, books, chat endpoints
- RAG pipeline: PyMuPDF -> chunking -> embeddings -> ChromaDB -> hybrid retrieval
- Tutor agent with SSE streaming
- Next.js frontend with library/upload and chat pages
- Upload validation, CORS fixes, SSE robustness

### Phase 2 MVP (Router + 4 Agents) - COMPLETE

- LangGraph orchestration: retrieve -> route -> agent prep -> stream
- 4 intent types: `explain`, `example`, `context`, `quiz`
- Agents: Tutor, Example Generator, Context Enricher, Quiz Master
- Router: deterministic keyword matching, context > quiz > example > explain fallback
- Config flag: `phase2_routing_enabled` (default `True`)
- Frontend: agent labels, structured source cards, page filters, copy-citation

### SQLite Progress-Tracking + Session Persistence - COMPLETE

- Database module with 3-table schema: `books`, `chat_sessions`, `chat_messages`
- Storage provider layer for transparent JSON/SQLite switching
- JSON-to-SQLite migration helper
- Session-aware chat: creates sessions, persists messages, emits `session` SSE event
- Session resume: `session_id` in chat request loads history from DB
- Session API: `GET /api/sessions/book/{book_id}`, `GET /api/sessions/{session_id}/messages`
- Config flag: `use_sqlite_storage` (default `False`, ready to enable)
- Frontend: sessions sidebar with resume/new-session controls

## Test suite summary

| Test file | Tests | Status |
|-----------|-------|--------|
| `test_chat_stream_integration.py` | 11 | Pass |
| `test_router.py` | 16 | Pass |
| `test_session_chat_integration.py` | 5 | Pass |
| `test_sessions.py` | 6 | Pass |
| `test_sse_contract.py` | 4 | Pass |
| `test_storage_db.py` | 5 | Pass |
| **Total** | **46** | **All pass** |

## Key files added/changed this session

### New files
- `backend/app/agents/quiz_master.py` - Quiz Master prompt
- `backend/app/api/routes/sessions.py` - Session list/messages endpoints
- `backend/app/services/storage_provider.py` - JSON/SQLite storage switch
- `backend/app/services/migrate.py` - JSON-to-SQLite migration
- `backend/tests/test_session_chat_integration.py` - Session-aware chat tests
- `docs/specs/2026-03-28-sqlite-progress-tracking.md`
- `docs/specs/2026-03-28-quiz-master-agent.md`
- `docs/devlog/2026-03-28-phase2-mvp-complete.md`
- `docs/devlog/2026-03-28-sqlite-progress-tracking-foundation.md`
- `docs/devlog/2026-03-28-session-persistence-and-quiz-master.md`

### Modified files
- `backend/app/agents/router.py` - Added quiz intent
- `backend/app/agents/graph.py` - Added quiz_prep node
- `backend/app/api/routes/chat.py` - Session-aware streaming
- `backend/app/api/routes/books.py` - Uses storage_provider
- `backend/app/main.py` - Sessions router registered
- `backend/app/config.py` - `use_sqlite_storage` flag
- `backend/app/schemas.py` - SessionResponse, session_id in ChatRequest
- `backend/requirements.txt` - aiosqlite, pytest-asyncio, pytest pinned
- `backend/tests/test_router.py` - Quiz intent tests
- `backend/tests/test_chat_stream_integration.py` - Quiz SSE test
- `frontend/src/lib/api.ts` - Session API helpers
- `frontend/src/app/chat/[bookId]/page.tsx` - Session sidebar + Quiz Master label
- `frontend/src/app/page.tsx` - Updated branding

## Important decisions already made

- Do not use LiteLLM; use LangChain chat models
- Solo workflow: direct commits to `master`
- `aiosqlite` for async SQLite; `pytest<9` required by `pytest-asyncio` 0.26.0
- Storage provider pattern for transparent backend swap
- Quiz classification uses keyword matching consistent with existing router

See ADRs:
- `docs/adr/0001-langchain-over-litellm.md`
- `docs/adr/0002-langgraph-for-orchestration.md`
- `docs/adr/0003-phase1-local-storage-and-sse.md`

## Run without Docker (preferred on this machine)

1. Backend:

```powershell
cd C:\Users\Celavi\Documents\HelpMeLearn\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

2. Frontend:

```powershell
cd C:\Users\Celavi\Documents\HelpMeLearn\frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

3. Verify:
- Frontend: `http://127.0.0.1:3000`
- Backend docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/health`

## Known gotchas

- Port conflict on backend startup (`WinError 10048`): `netstat -ano | findstr :8000` then `taskkill /PID <PID> /F`
- Browser origin mismatch (`localhost` vs `127.0.0.1`) can trigger CORS issues
- `pytest-asyncio` 0.26.0 needs `pytest<9`; pinned at 8.4.2

## Suggested next work

1. Enable `use_sqlite_storage=True` by default and run JSON-to-SQLite migration
2. Add quiz answer evaluation flow (user answers -> Quiz Master grades and explains)
3. Plan Study Planner agent for structured learning paths
4. Add learning progress / mastery tracking tables to SQLite schema
5. Consider spaced repetition scheduling based on quiz scores
