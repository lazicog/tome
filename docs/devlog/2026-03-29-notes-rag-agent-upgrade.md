# 2026-03-29: Notes, RAG v2, and Agent System Upgrade

Implementation of the plan documented in the project roadmap (LLM router, query rewriting, cross-encoder reranking, contextual chunks, richer sources, SQLite notes, Summarizer agent, and a Notes panel in the book study UI).

## What was done

### Phase A: LLM-based router

- Replaced pure keyword routing with `classify_intent_llm()` in `backend/app/agents/router.py`: short system prompt + recent history, JSON output with intent only.
- Fallback `_classify_intent_keyword()` when the LLM call fails (network, parse, invalid intent).
- New intent: `summarize` (study notes / key takeaways). Existing intents: `explain`, `example`, `context`, `quiz`.
- Sync `classify_intent()` retained for tests and backward compatibility; it delegates to keyword fallback only.

### Phase B: RAG pipeline

- **Query rewriting** (`query_rewrite_node` in `backend/app/agents/graph.py`): optional LLM step produces 2–3 search strings; retrieval merges and deduplicates by chunk id. Toggle: `query_rewrite_enabled` (default `True`).
- **Cross-encoder reranking** (`backend/app/rag/reranker.py`): `cross-encoder/ms-marco-MiniLM-L-6-v2` re-scores hybrid candidates before returning top-k. Toggle: `reranker_enabled` (default `True`), model: `reranker_model`.
- **Contextual chunks** (`backend/app/rag/chunker.py`): each chunk body is prefixed with `[Chapter: … | Section: …]` before embedding for better semantic retrieval. Requires **re-ingest** for existing books.
- **Richer sources** (`backend/app/agents/tutor.py`): `_format_sources` adds `quote` (short excerpt), `relevance` (high/medium/low from score), and deduplicates by chapter+page key.

### Phase C: Notes

- **Schema** (`backend/app/services/database.py`): `notes` table with FK to `books`, optional FK to `chat_messages` for `source_message_id`.
- **Service** (`backend/app/services/notes.py`): async CRUD, list with filters (`page`, `type`, `search` substring on title/content).
- **API** (`backend/app/api/routes/notes.py`): `POST/GET /api/books/{book_id}/notes`, `GET/PUT/DELETE /api/notes/{note_id}`, `POST /api/books/{book_id}/notes/generate?query=…` (SSE streaming + auto-save as `ai_summary`).
- **Summarizer** (`backend/app/agents/summarizer.py`): prompt for structured study notes; wired via `summarize_prep` in the graph.
- **Chat tool behavior** (`backend/app/api/routes/chat.py`): when SQLite sessions are enabled and the routed agent is `summarize`, assistant response is persisted as usual and an `ai_summary` note is created; `note_saved` SSE event notifies the client.

### Phase D: Frontend

- `frontend/src/lib/api.ts`: `Note`, `NoteCreate`, `listNotes`, `createNote`, `updateNote`, `deleteNote`.
- `frontend/src/app/book/[bookId]/page.tsx`: Chat | Notes tabs, save-as-note on assistant messages, notes CRUD, search, type filter, highlight shortcut, page jump from notes, handling `note_saved` SSE for toasts.
- `frontend/src/components/PdfViewer.tsx`: `onPageChange` so notes can default to the current reader page.

### Tests and docs

- Backend: `test_notes.py` (10 tests), expanded `test_router.py`, integration test patches for `classify_intent_llm` + `query_rewrite_enabled` where needed.
- `docs/SESSION-HANDOFF.md` updated with architecture, APIs, config flags, and test count (63).

## Key decisions made

- **Router**: LLM-first with keyword fallback keeps production resilient without API keys in tests (monkeypatch in integration tests).
- **Graph order**: `START → router → query_rewrite → retrieve → route_intent → *_prep → END`; retrieval runs after intent is known but `route_intent` only selects `system_prompt`—retrieval uses merged queries from rewrite, not per-intent separate indexes.
- **Reranker**: Applied after hybrid fusion on all candidates above score threshold; final score exposed as `rerank_score` when enabled.
- **Notes**: SQLite-only for the `notes` table (same as other feature tables); notes API requires existing `books` row (FK).

## Issues / Gotchas

- **Re-ingest**: Contextual headers change stored chunks; old Chroma collections should be rebuilt via `POST /api/books/{book_id}/reingest` or UI button.
- **Cross-encoder**: First request downloads the model (~22MB); cold start adds latency.
- **LLM router + query rewrite**: Two extra LLM calls per chat message when both are enabled; disable via config for local dev or tests.
- **Summarize auto-save**: `note_saved` and DB insert only run on the SQLite session path when `agent_type == "summarize"` after streaming completes.

## Next steps

- Optional: `study_plan` intent and dedicated agent (plan only referenced summarize).
- `tool_result` SSE for richer agent tooling beyond auto-save.
- Export notes (Markdown/PDF).
- Evaluation: retrieval quality metrics on a fixed query set.
