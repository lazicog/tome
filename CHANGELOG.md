# Changelog

All notable changes to HelpMeLearn will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Single orchestrator agent** (see `docs/devlog/2026-03-30-orchestrator-pdf-viewer.md`):
  - Replaced 5-agent LangGraph routing system with a single tool-calling orchestrator
  - Tools: `search_book`, `get_page_text`, `save_note`, `generate_quiz`, `web_search` (opt-in via `WEB_SEARCH_ENABLED`)
  - Current page text injected verbatim into system prompt — agent knows exactly what the user is reading
  - `thinking` SSE event emitted during each tool call ("Searching book…", "Reading page…", "Saving note…")
  - `web_sources` SSE event for web search results (Tavily → DuckDuckGo fallback)
  - `backend/app/rag/page_extractor.py` — pdfplumber verbatim page text extraction
  - `backend/app/agents/tools.py` — 5 LangChain `@tool` functions with shared closure state
  - `backend/app/agents/orchestrator.py` — streaming agentic loop with `astream_events`
  - Deleted: `router.py`, `example_gen.py`, `context_enricher.py`, `quiz_master.py`, `summarizer.py`
  - Config: `web_search_enabled` (default `false`), `tavily_api_key`
- **react-pdf PDF viewer** — replaced browser iframe with canvas renderer:
  - Continuous scroll (all pages rendered), IntersectionObserver page tracking, fit-to-width zoom
  - Smooth keyboard scroll (rAF loop, ArrowUp/Down 20px/frame), instant page jumps (ArrowLeft/Right)
  - Bottom toolbar: prev/next, page number input, zoom controls; text selection enabled
  - `/` keyboard shortcut focuses chat input from anywhere on the page
- **LLM-suggested note titles** — "Save as note" opens dialog with AI-generated title (editable before saving)
- **Phoenix observability spec** written at `docs/specs/2026-03-30-phoenix-eval-pipeline.md` — implementation in progress

### Changed
- `graph.py` reduced to thin wrapper (6 lines) delegating to orchestrator
- `tutor.py` now utility-only (`_sse_event`, `_format_sources`, `build_context`, `_history_to_messages`)
- `chat.py` simplified — removed `_note_aware_stream` and `phase2_routing_enabled` fallback path
- Frontend: removed agent label from message bubbles; added `thinking` label + web sources UI

### Notes, RAG v2, and agent upgrade
- **Notes, RAG v2, and agent upgrade** (see `docs/devlog/2026-03-29-notes-rag-agent-upgrade.md`):
  - LLM intent router with keyword fallback; new `summarize` intent and Summarizer agent
  - LangGraph flow: `router → query_rewrite → retrieve → agent prep` (config: `query_rewrite_enabled`, `reranker_enabled`, `reranker_model`)
  - Cross-encoder reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`) after hybrid vector + BM25 fusion
  - Contextual chunk headers (`[Chapter | Section]`) prepended at ingest; **re-ingest** required for existing books
  - Sources API: `quote`, `relevance` (high/medium/low), deduplicated chunks
  - SQLite `notes` table: types `manual`, `ai_summary`, `highlight`, `agent_insight`
  - Notes REST API + `POST /api/books/{book_id}/notes/generate` (SSE); `note_saved` SSE when summarizer saves via session chat
  - Frontend: Chat | Notes tabs, note CRUD, search/filter, save-as-note, PDF page sync via `PdfViewer`
- SQLite progress-tracking foundation:
  - Database schema for books, chat sessions, and chat messages
  - Async service layer for book CRUD (`storage_db.py`) and session/message CRUD (`sessions.py`)
  - Config flag `use_sqlite_storage` for opt-in SQLite backend (default off)
  - Storage provider layer (`storage_provider.py`) for transparent JSON/SQLite switching
  - JSON-to-SQLite migration helper (`migrate.py`)
  - Unit tests for all SQLite service operations
- Session-aware chat:
  - Chat route creates sessions and persists user/assistant messages when SQLite is enabled
  - `session` SSE event emits session ID to frontend
  - Session resume via `session_id` field in chat request (loads history from DB)
- Session API endpoints:
  - `GET /api/sessions/book/{book_id}` lists sessions with message counts
  - `GET /api/sessions/{session_id}/messages` retrieves full conversation history
- Quiz Master agent:
  - `quiz` intent in router (keywords: quiz, test me, assess, practice, etc.)
  - `QUIZ_PROMPT` generates 3-5 mixed questions from RAG context
  - `quiz_prep` node integrated into LangGraph orchestration graph
- Frontend session sidebar:
  - Sessions list with resume and new-session controls
  - Enter key support for sending messages
  - Updated home page branding

### Changed
- Router now classifies 4 intents: `context` > `quiz` > `example` > `explain` (fallback)
- Chat UI agent label map now includes "Quiz Master" for quiz intent
- Books and chat routes now import from `storage_provider` instead of `storage` directly

## [0.2.0] - 2026-03-28

Phase 2 MVP: Router + 3 Specialized Agents

### Added
- Project architecture and phased implementation plan
- 6 Cursor rules for automated code convention enforcement (project overview, Python backend, agent development, RAG pipeline, frontend Next.js, API design)
- 4 Cursor skills for domain expertise (LangGraph agents, PDF RAG pipeline, LangChain LLM providers, open-source packaging)
- Documentation system with Architecture Decision Records, development log, and changelog
- Multi-provider LLM support design via LangChain chat models (OpenAI, Anthropic, Ollama)
- Phase 1 backend scaffold with FastAPI routes for health, books upload/list/get, and chat streaming
- PDF ingestion pipeline: PyMuPDF extraction, semantic chunking with overlap, sentence-transformers embeddings, ChromaDB storage
- Hybrid retrieval baseline combining vector search and BM25 scoring
- Tutor agent streaming answers with source chunk citations over SSE
- Phase 1 frontend scaffold (Next.js) with library/upload view and per-book chat page
- Docker Compose setup and root `.env.example` + project README quick start
- Spec-first workflow support:
  - always-on spec rule in `.cursor/rules/specs.mdc`
  - `spec-authoring` skill in `.cursor/skills/spec-authoring/`
  - `docs/specs/` directory with naming and template guidance
- Phase 2 MVP implementation scaffold:
  - LangGraph routing graph for `explain` / `example` / `context`
  - specialized prompt modules for Example Generator and Context Enricher
  - chat route integration with routed graph path
- Route and SSE regression tests:
  - router phrase matrix for `explain` / `example` / `context`
  - SSE event contract checks for `agent` and `done`
- API-level routed chat integration test for SSE event ordering (`agent` -> `token` -> `sources` -> `done`)
- API-level fallback Tutor chat integration test when routing is disabled (`phase2_routing_enabled=false`)
- API-level upload -> ready -> routed chat integration test (book lifecycle plus SSE stream contract)
- Multi-agent collaboration assets:
  - `docs/workflows/multi-agent-worktree-playbook.md`
  - specialized Cursor skills for coordinator, feature builder, reviewer, and integration manager
- Frontend chat manual QA checklist for stream, source UX, and failure-path regression checks
- API-level routed intent matrix tests (`explain`, `example`, `context`) with active router path and LLM stub
- API-level assertions that routed streams emit `sources` exactly once with required source fields
- API integration tests for chat error paths (`404` book missing, `400` book still processing)
- API integration tests now cover all non-ready chat statuses (`queued`, `processing`, `failed`) for `400` responses

### Changed
- Frontend now auto-refreshes book status while ingestion is in progress and only enables chat links once a book is ready
- SSE parsing in chat page now supports multi-line `data:` frames for better stream compatibility
- Backend streaming utility now supports prompt-driven routed responses while preserving SSE event contract
- Chat UI now displays routed assistant label (`Tutor`, `Example Agent`, `Context Enricher`) from backend stream events
- Example Generator and Context Enricher prompts are tuned for clearer role-specific behavior
- Chat UI now renders structured source cards (chapter/section/pages/score) instead of raw source JSON
- Chat sources now support per-page filtering and one-click citation copy in the chat UI
- Chat stream client now guarantees `Thinking...` clears on stream/parse failures and surfaces a friendly retry error

### Fixed
- Upload endpoint now enforces max upload size and rejects empty uploads with clear errors
- ChromaDB metadata serialization now stores scalar-safe values and reconstructs `page_numbers` on retrieval
- CORS defaults now allow both `http://localhost:3000` and `http://127.0.0.1:3000` for local development
- Routed and fallback chat paths now emit explicit `agent` stream events so routing is visible to the user
- Router no longer overweights prior history terms (for example, earlier "code example") when classifying the current user turn
