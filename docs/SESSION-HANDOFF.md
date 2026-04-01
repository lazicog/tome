# Tome Session Handoff

Use this file as the startup context when resuming work with the agent.

## How to resume

At the start of the next session, say:

`Read docs/SESSION-HANDOFF.md and continue from there.`

Devlogs for context:
- Modes, model picker, color pass: `docs/devlog/2026-04-02-modes-model-picker-color.md`
- PDF viewer UX polish: `docs/devlog/2026-03-31-pdf-viewer-ux-polish.md`
- Orchestrator overhaul + PDF viewer: `docs/devlog/2026-03-30-orchestrator-pdf-viewer.md`
- Notes + RAG v2 + agent upgrade: `docs/devlog/2026-03-29-notes-rag-agent-upgrade.md`

## Current project status

- Project: `tome` (https://github.com/lazicog/tome)
- Branch: `master`
- Workflow: solo mode, direct commits to `master`

---

## What is completed

### Foundation and conventions — COMPLETE
- Cursor rules, skills, spec-first workflow, docs system (ADRs, devlog, changelog)

### Phase 1 (scaffold + hardening) — COMPLETE
- FastAPI backend, RAG pipeline, Tutor agent, Next.js frontend, upload validation

### Phase 2 MVP (Router + Agents) — COMPLETE (superseded by orchestrator)
- LangGraph pipeline, 4 intent types, LLM router, query rewrite, cross-encoder reranking

### SQLite Persistence — COMPLETE
- 4-table schema (books, chat_sessions, chat_messages, notes), session-aware chat, session resume/list API

### RAG Pipeline v2 — COMPLETE
- Heading-aware chunking, contextual chunk enrichment, hybrid vector+BM25, cross-encoder reranking, query rewriting

### Notes System — COMPLETE
- SQLite notes table, full CRUD API, AI generation endpoint, chat integration (note_saved SSE)

### Single Orchestrator Agent — COMPLETE (2026-03-30)
- Replaced 5-agent LangGraph with single tool-calling orchestrator
- Tools: search_book, get_page_text, save_note, list_notes, update_note, generate_quiz, web_search (opt-in)
- Current page text injected verbatim into system prompt
- `thinking` SSE events during tool execution; `web_sources` SSE for web results
- LLM-suggested note titles with editable dialog before saving

### Phoenix + Eval Pipeline — COMPLETE (2026-03-30)
- `phoenix_enabled` / `phoenix_endpoint` in `config.py`
- LangChain OTel instrumentation in `main.py` lifespan
- `evals` table in SQLite database
- `services/evals.py` CRUD
- `agents/evaluator.py` LLM-as-judge (faithfulness + helpfulness scores)
- `EvalMetadata` yielded from orchestrator after stream; `_fire_eval()` in `chat.py` fires background task
- `GET /api/debug/evals` endpoint

### react-pdf PDF Viewer — COMPLETE (2026-03-30)
- Replaced iframe with react-pdf v7 canvas renderer
- Continuous scroll, IntersectionObserver page tracking, fit-to-width zoom
- rAF-loop keyboard scroll, instant page jumps, bottom toolbar

### PDF Viewer UX Polish — COMPLETE (2026-03-31)
- Virtual page rendering — 9-page sliding window, `estPageHeight` placeholders; fixes 350+ page perf
- Reading mode — chat-closed expands to full width, centered at max-w-4xl with depth shadow
- Left progress rail + right rail large click zones (chat 80% / notes 20%)
- Chat toggle button on divider edge; browser scrollbar removed

### Multi-Agent Modes (Learn / Research) — COMPLETE (2026-04-02)
- Mode selector bar: `[ Learn ]  [ Research ]  [ Visualize (stub) ]`
- Research mode: always-on web search, `RESEARCH_SYSTEM_PROMPT`, three-part output format (Book says / Current practice / Where they differ), no quiz tool
- `mode` field on `ChatRequest`; forwarded through full call stack; "Research" badge on messages
- 7 new tests in `tests/test_modes.py`

### Per-Request Model Picker — COMPLETE (2026-04-02)
- `AVAILABLE_MODELS` in `config.py`: GPT-5.4 mini, GPT-5.4, Claude Haiku, Claude Sonnet, Claude Opus
- `GET /api/models` endpoint — filters by configured API keys
- `model_id` on `ChatRequest`; `_resolve_model()` in orchestrator; forwarded through full call stack
- Frontend: `<select>` in mode bar, `localStorage` persistence, model label badge on messages
- 6 new tests in `tests/test_models_endpoint.py`

### Unified Sage Accent — COMPLETE (2026-04-02)
- Single `#6B9B6B` across all UI; fixed all leftover indigo tints
- 1px fixed top accent bar in `layout.tsx`
- Sage tint on source card icons and progress rail counter

---

## Test suite

83 tests, all passing.
Run: `cd backend && python -m pytest -q`

| File | Tests |
|---|---|
| test_chat_stream_integration.py | 8 |
| test_modes.py | 7 |
| test_models_endpoint.py | 6 |
| test_router.py | 5 |
| test_session_chat_integration.py | 5 |
| test_sessions.py | 6 |
| test_notes.py | 10 |
| test_sse_contract.py | 4 |
| test_storage_db.py | 5 |
| test_position_filter.py | 15 |
| test_evals.py | ? |

---

## Immediate next steps (candidates — pick one)

### Option A: Eval dashboard UI
- The `/api/debug/evals` endpoint exists but there is no frontend for it.
- A simple table showing faithfulness/helpfulness scores per session would close the loop on observability.

### Option B: PDF text highlights as notes
- The `notes` table has a `highlight` type; `NoteCreate.type` supports it.
- No UI yet to select text in the PDF viewer and save it as a highlight note.
- Would require a `mouseup` listener on the react-pdf text layer + a small inline save popover.

### Option C: Book progress persistence
- Current page is not saved between sessions; re-opening a book always starts at page 1.
- Could store `last_page` in the `books` SQLite table and restore it on load.

### Option D: Note export
- Export all notes for a book as a single markdown file.
- Simple `GET /api/books/{book_id}/notes/export` endpoint returning markdown.

---

## Run without Docker

```bash
# Backend
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000

# Phoenix (when PHOENIX_ENABLED=true in .env)
cd backend
python -m phoenix.server.main
# UI at http://localhost:6006
```

---

## Key architectural decisions

- LLM framework: LangChain (tool-calling support, multi-provider)
- Orchestration: Single tool-calling agent (not LangGraph multi-agent)
- PDF viewer: react-pdf v7 (v9 pdfjs-dist ESM incompatible with Next.js 15 webpack)
- Storage: SQLite via aiosqlite
- Observability: Arize Phoenix (no Docker, local Python process)
- Eval approach: LLM-as-judge (faithfulness + helpfulness scores in SQLite)
- Web search: Tavily primary, DuckDuckGo fallback, opt-in via `WEB_SEARCH_ENABLED=true`; always-on in Research mode
- Model selection: per-request via `model_id` in `ChatRequest`; `AVAILABLE_MODELS` filtered by configured keys
- Solo workflow: Direct commits to master
- GitHub operations: use `gh` CLI (not raw git remote commands)

---

## Known gotchas

- Port conflict: `netstat -ano | findstr :8000` → `taskkill /PID <PID> /F`
- localhost vs 127.0.0.1 mismatch triggers CORS errors
- PowerShell: use `;` not `&&` between commands
- react-pdf v7 worker URL must be `.min.js` not `.min.mjs`
- Existing books need re-ingest after chunker changes
- LLM tool-calling requires function-calling capable model (GPT-4o-mini, Claude 3.x+)
- `WEB_SEARCH_ENABLED=false` by default — Research mode overrides this per-request
- Stale `.next` cache can cause webpack chunk errors — delete `.next/` if mysterious module-not-found errors appear
- Mock signatures for `stream_routed_answer` in integration tests must include all keyword args (`mode`, `model_id`) — update when adding new params
