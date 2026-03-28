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

- Database module with 4-table schema: `books`, `chat_sessions`, `chat_messages`, `notes`
- Storage provider layer for transparent JSON/SQLite switching
- JSON-to-SQLite migration helper
- Session-aware chat: creates sessions, persists messages, emits `session` SSE event
- Session resume: `session_id` in chat request loads history from DB
- Session API: `GET /api/sessions/book/{book_id}`, `GET /api/sessions/{session_id}/messages`
- Config flag: `use_sqlite_storage` (default `False`, ready to enable)

### RAG Pipeline Overhaul + v2 Improvements - COMPLETE

- Removed silent hash-based fallback embedding (errors now surface immediately)
- Added structured logging with `structlog` across embeddings, retriever, chunker, ingest
- Startup diagnostics: config summary + eager embedding model load in app lifespan
- Heading-aware chunking: PDF processor extracts font metadata, chunker detects chapter/section headings by font size
- Contextual chunk enrichment: `[Chapter: X | Section: Y]` header prepended to each chunk before embedding
- Retrieval tuning: `top_k` increased to 8, prefetch multiplier 5x, score threshold 0.15
- Cross-encoder reranking: `cross-encoder/ms-marco-MiniLM-L-6-v2` re-scores candidates after hybrid fusion
- Query rewriting: LLM generates 2-3 optimized search queries, results merged + deduped
- Better source display: relevant quote extraction, relevance labels (high/medium/low), deduplication
- Debug endpoint: `GET /api/debug/retrieve?book_id=...&query=...&k=8`
- Reingest endpoint: `POST /api/books/{book_id}/reingest` (deletes + re-ingests with new pipeline)
- PDF serve endpoint: `GET /api/books/{book_id}/pdf` (serves uploaded PDF to frontend viewer)
- Config flags: `reranker_enabled` (default `True`), `query_rewrite_enabled` (default `True`)

### Agent System Upgrade - COMPLETE

- LLM-based intent router: replaces keyword matching with structured LLM classification
- Keyword fallback: automatic when LLM routing fails
- 5 intent types: `explain`, `example`, `context`, `quiz`, `summarize`
- New Summarizer agent: generates structured study notes from retrieved context
- LangGraph flow: `router -> query_rewrite -> retrieve -> conditional agent prep -> stream`
- Agent tool use: summarize intent auto-saves output as notes via `note_saved` SSE event

### Note-Taking System - COMPLETE

- `notes` table in SQLite: id, book_id, page_number, chapter, title, content, type, source_message_id, tags, timestamps
- Note types: `manual`, `ai_summary`, `highlight`, `agent_insight`
- Notes service: full CRUD with search and filtering
- Notes API: `POST/GET /api/books/{book_id}/notes`, `GET/PUT/DELETE /api/notes/{note_id}`
- AI note generation: `POST /api/books/{book_id}/notes/generate?query=...` (SSE with auto-save)
- Chat integration: summarize agent auto-saves notes, `note_saved` SSE event emitted

### Frontend Redesign + UX Polish + Notes Panel - COMPLETE

- Tailwind CSS v4 + PostCSS configured with custom dark theme tokens
- Utility libraries: `clsx`, `tailwind-merge`, `class-variance-authority`, `lucide-react`
- Responsive nav bar with sticky positioning and backdrop blur
- Home/library page:
  - Drag-and-drop upload zone, book cards with status badges + created date
  - Re-ingest button, delete book button with confirmation
  - Toast notifications for upload, reingest, delete actions
  - Better empty state with icon
- Split-pane book study page (`/book/[bookId]`):
  - Left panel: PDF reader via iframe (browser-native), smooth page navigation
  - Right panel: Tabbed Chat | Notes interface
  - Resizable split pane with drag handle (25%-75% range)
  - Toggle buttons for Chat, Notes, and close panel
- Chat UX:
  - Auto-expanding textarea with Shift+Enter for newlines, Enter to send
  - 5 starter suggestion chips (explain, example, context, quiz, summarize)
  - Typing indicator (pulsing dots) before first token arrives
  - "Save as note" button on each assistant message
  - Source chips with relevance badges (high/medium/low) and quote tooltips
  - Dark theme markdown styling: code blocks, headings, tables, blockquotes
  - Keyboard shortcut hint below input
- Notes panel:
  - Note list with type badges (Manual, AI Summary, Highlight, Saved Insight)
  - Inline note editor for create/edit
  - Search bar for full-text search across notes
  - Type filter dropdown (all, manual, ai_summary, highlight, agent_insight)
  - "Add highlight" button pre-fills current page number
  - Page and chapter references on each note, clickable to navigate PDF
  - Edit and delete buttons on each note card
  - Auto-refresh when AI generates notes via chat
  - Toast notification when notes are auto-saved by summarizer agent
- Delete book API: `DELETE /api/books/{book_id}` with cascade (PDF, embeddings, DB record)

## Test suite summary

| Test file | Tests | Status |
|-----------|-------|--------|
| `test_chat_stream_integration.py` | 11 | Pass |
| `test_notes.py` | 10 | Pass |
| `test_router.py` | 22 | Pass |
| `test_session_chat_integration.py` | 5 | Pass |
| `test_sessions.py` | 6 | Pass |
| `test_sse_contract.py` | 4 | Pass |
| `test_storage_db.py` | 5 | Pass |
| **Total** | **63** | **All pass** |

## Key files added/changed this session

### New files (Notes + RAG + Agent upgrade)
- `backend/app/agents/summarizer.py` - Summarizer agent prompt
- `backend/app/rag/reranker.py` - Cross-encoder reranking module
- `backend/app/api/routes/notes.py` - Notes CRUD + AI generation API
- `backend/app/services/notes.py` - Notes SQLite persistence service
- `backend/tests/test_notes.py` - Notes service unit tests (10 tests)

### Modified files (Notes + RAG + Agent upgrade)
- `backend/app/agents/router.py` - LLM-based intent classification with keyword fallback, new `summarize` intent
- `backend/app/agents/graph.py` - LangGraph rewired: router -> query_rewrite -> retrieve -> agent prep, new summarize_prep node
- `backend/app/rag/retriever.py` - Cross-encoder reranking integration after hybrid fusion
- `backend/app/rag/chunker.py` - Contextual chunk enrichment (chapter/section headers prepended)
- `backend/app/agents/tutor.py` - Quote extraction, relevance labels, source deduplication in `_format_sources`
- `backend/app/config.py` - Added `reranker_model`, `reranker_enabled`, `query_rewrite_enabled`
- `backend/app/schemas.py` - Added `NoteCreate`, `NoteUpdate`, `NoteResponse` models; extended `SourceChunk` with `relevance` and `quote`
- `backend/app/services/database.py` - Added `notes` table to schema
- `backend/app/api/routes/chat.py` - Auto-save summarize output as notes, emit `note_saved` SSE event
- `backend/app/main.py` - Registered notes router
- `backend/tests/test_router.py` - Updated for LLM router, added summarize intent tests (22 tests)
- `backend/tests/test_chat_stream_integration.py` - Updated monkeypatches for LLM router
- `frontend/src/lib/api.ts` - Added `Note`, `NoteCreate` types and `listNotes`, `createNote`, `updateNote`, `deleteNote` helpers
- `frontend/src/app/book/[bookId]/page.tsx` - Tabbed Chat|Notes panel, save-as-note, note CRUD, highlights, search
- `frontend/src/components/PdfViewer.tsx` - Added `onPageChange` callback
- `frontend/src/app/globals.css` - Added `animate-toast-in` utility

### Previous session files (still present)
- `backend/app/agents/quiz_master.py` - Quiz Master prompt
- `backend/app/api/routes/sessions.py` - Session list/messages endpoints
- `backend/app/api/routes/debug.py` - Debug retrieve endpoint
- `backend/app/services/storage_provider.py` - JSON/SQLite storage switch
- `backend/app/services/migrate.py` - JSON-to-SQLite migration
- Specs, devlogs, ADRs as previously documented

## Important decisions already made

- Do not use LiteLLM; use LangChain chat models
- Solo workflow: direct commits to `master`
- `aiosqlite` for async SQLite; `pytest<9` required by `pytest-asyncio` 0.26.0
- Storage provider pattern for transparent backend swap
- LLM-based router with keyword fallback (replaces pure keyword matching)
- Cross-encoder reranking after hybrid vector+BM25 fusion
- Query rewriting via LLM for better retrieval on vague queries
- Contextual chunk enrichment: `[Chapter: X | Section: Y]` header on each chunk
- Silent embedding fallback removed (errors surface immediately for debugging)
- Heading detection uses font size ratios: chapter >= 1.4x body, section >= 1.1x body
- Frontend uses Tailwind CSS v4 + custom theme tokens (not shadcn/ui component library install, just its utility pattern)
- Switched from `react-pdf` to browser-native iframe PDF rendering (pdfjs-dist incompatible with Next.js 15 webpack)
- PDF served from backend `/api/books/{book_id}/pdf` with `Content-Disposition: inline`
- Notes auto-saved by summarizer agent via SSE `note_saved` event

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
- Cross-encoder reranker model downloads on first use (~22MB); subsequent loads are from cache
- LLM router adds ~200-500ms latency per query for intent classification

## Suggested next work

1. **Re-ingest test book** with the new contextual chunking + cross-encoder pipeline (click re-ingest button or call API)
2. Enable `use_sqlite_storage=True` by default and run JSON-to-SQLite migration
3. Add quiz answer evaluation flow (user answers -> Quiz Master grades and explains)
4. Plan Study Planner agent for structured learning paths
5. Add learning progress / mastery tracking tables to SQLite schema
6. Consider spaced repetition scheduling based on quiz scores
7. Add note export functionality (markdown / PDF)
8. Consider PDF text selection highlighting via a custom PDF renderer
