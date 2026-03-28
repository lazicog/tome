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

### SQLite Progress-Tracking + Session Persistence - COMPLETE

- Database module with 3-table schema: `books`, `chat_sessions`, `chat_messages`
- Storage provider layer for transparent JSON/SQLite switching
- JSON-to-SQLite migration helper
- Session-aware chat: creates sessions, persists messages, emits `session` SSE event
- Session resume: `session_id` in chat request loads history from DB
- Session API: `GET /api/sessions/book/{book_id}`, `GET /api/sessions/{session_id}/messages`
- Config flag: `use_sqlite_storage` (default `False`, ready to enable)

### RAG Pipeline Overhaul - COMPLETE

- Removed silent hash-based fallback embedding (errors now surface immediately)
- Added structured logging with `structlog` across embeddings, retriever, chunker, ingest
- Startup diagnostics: config summary + eager embedding model load in app lifespan
- Heading-aware chunking: PDF processor extracts font metadata, chunker detects chapter/section headings by font size
- Retrieval tuning: `top_k` increased to 8, prefetch multiplier 5x, score threshold 0.15
- Debug endpoint: `GET /api/debug/retrieve?book_id=...&query=...&k=8`
- Reingest endpoint: `POST /api/books/{book_id}/reingest` (deletes + re-ingests with new pipeline)
- PDF serve endpoint: `GET /api/books/{book_id}/pdf` (serves uploaded PDF to frontend viewer)

### Frontend Redesign + UX Polish - COMPLETE

- Tailwind CSS v4 + PostCSS configured with custom dark theme tokens
- Utility libraries: `clsx`, `tailwind-merge`, `class-variance-authority`, `lucide-react`
- Responsive nav bar with sticky positioning and backdrop blur
- Home/library page:
  - Drag-and-drop upload zone, book cards with status badges + created date
  - Re-ingest button, delete book button with confirmation
  - Toast notifications for upload, reingest, delete actions
  - Better empty state with icon
- Split-pane book study page (`/book/[bookId]`):
  - Left panel: PDF reader via iframe (browser-native), smooth page navigation without cover flash
  - Right panel: Chat with session tabs, markdown rendering (`react-markdown`), source chips with chapter names
  - Resizable split pane with drag handle (25%-75% range)
  - Toggle button to show/hide chat panel
- Chat UX:
  - Auto-expanding textarea with Shift+Enter for newlines, Enter to send
  - Starter suggestion chips in empty state ("Explain the main concepts", "Quiz me", etc.)
  - Typing indicator (pulsing dots) before first token arrives
  - Dark theme markdown styling: code blocks, headings, tables, blockquotes
  - Keyboard shortcut hint below input
- Delete book API: `DELETE /api/books/{book_id}` with cascade (PDF, embeddings, DB record)
- Old `/chat/[bookId]` route removed

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

### New files (RAG overhaul + frontend redesign + UX polish)
- `backend/app/api/routes/debug.py` - Debug retrieve endpoint
- `frontend/postcss.config.mjs` - PostCSS config for Tailwind v4
- `frontend/src/app/globals.css` - Tailwind imports + dark theme tokens + prose styles + animations
- `frontend/src/lib/utils.ts` - `cn()` utility (clsx + tailwind-merge)
- `frontend/src/app/book/[bookId]/page.tsx` - Split-pane book reader + chat
- `frontend/src/components/PdfViewer.tsx` - Iframe-based PDF viewer with smooth navigation

### Modified files (RAG overhaul + frontend redesign + UX polish)
- `backend/app/rag/embeddings.py` - Removed silent fallback, added structlog
- `backend/app/rag/retriever.py` - Added logging, prefetch, score threshold, delete_collection
- `backend/app/rag/processor.py` - New `extract_pdf_pages()` with font metadata, kept legacy compat
- `backend/app/rag/chunker.py` - New `chunk_pages_rich()` heading-aware chunker, kept legacy compat
- `backend/app/rag/ingest.py` - Uses rich pipeline, added `reingest_book()`
- `backend/app/api/routes/books.py` - Reingest, PDF serve, delete endpoints + `_find_pdf_on_disk` helper
- `backend/app/main.py` - Lifespan startup diagnostics, debug router registered
- `backend/app/config.py` - Retrieval tuning params
- `backend/app/services/storage.py` - Added `delete_book`
- `backend/app/services/storage_db.py` - Added `delete_book`
- `backend/app/services/storage_provider.py` - Re-exports `delete_book`
- `frontend/src/app/layout.tsx` - Tailwind-based layout with nav bar
- `frontend/src/app/page.tsx` - Library with cards, badges, upload zone, toast, delete
- `frontend/src/lib/api.ts` - Added `getBook`, `reingestBook`, `deleteBook`, `getBookPdfUrl`, `getApiBase`
- `.gitignore` - Added `*.pdf` for test PDFs

### Deleted files
- `frontend/src/app/chat/[bookId]/page.tsx` - Replaced by `/book/[bookId]`

### Previous session files (still present)
- `backend/app/agents/quiz_master.py` - Quiz Master prompt
- `backend/app/api/routes/sessions.py` - Session list/messages endpoints
- `backend/app/services/storage_provider.py` - JSON/SQLite storage switch
- `backend/app/services/migrate.py` - JSON-to-SQLite migration
- `backend/tests/test_session_chat_integration.py` - Session-aware chat tests
- Specs, devlogs, ADRs as previously documented

## Important decisions already made

- Do not use LiteLLM; use LangChain chat models
- Solo workflow: direct commits to `master`
- `aiosqlite` for async SQLite; `pytest<9` required by `pytest-asyncio` 0.26.0
- Storage provider pattern for transparent backend swap
- Quiz classification uses keyword matching consistent with existing router
- Silent embedding fallback removed (errors surface immediately for debugging)
- Heading detection uses font size ratios: chapter >= 1.4x body, section >= 1.1x body
- Frontend uses Tailwind CSS v4 + custom theme tokens (not shadcn/ui component library install, just its utility pattern)
- Switched from `react-pdf` to browser-native iframe PDF rendering (pdfjs-dist incompatible with Next.js 15 webpack)
- PDF served from backend `/api/books/{book_id}/pdf` with `Content-Disposition: inline`

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
- PowerShell on this machine uses old version that doesn't support `&&`; use `;` or separate commands
- `npx`/`npm` not on default PATH in Cursor shell; use `$env:PATH = "C:\Program Files\nodejs;" + $env:PATH` first
- After RAG pipeline changes, existing books need re-ingestion: use the `/api/books/{book_id}/reingest` endpoint or the re-ingest button in the UI

## Suggested next work

1. **Re-ingest test book** with the new heading-aware pipeline (click re-ingest button or call API)
2. Enable `use_sqlite_storage=True` by default and run JSON-to-SQLite migration
3. Add quiz answer evaluation flow (user answers -> Quiz Master grades and explains)
4. Plan Study Planner agent for structured learning paths
5. Add learning progress / mastery tracking tables to SQLite schema
6. Consider spaced repetition scheduling based on quiz scores
