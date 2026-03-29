# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Tome

An AI-powered learning companion for technical PDFs. Users upload PDFs, then chat with specialized agents that explain, quiz, summarize, and contextualize content. Uses RAG (retrieval-augmented generation) for grounded responses.

## Commands

### Backend (FastAPI + Python)
```bash
cd backend
pip install -r requirements.txt   # Install dependencies
uvicorn app.main:app --reload     # Run dev server (port 8000)
pytest                            # Run all 63 tests
pytest tests/test_router.py       # Run a single test file
pytest -k "test_name"             # Run tests matching a name pattern
```

### Frontend (Next.js + TypeScript)
```bash
cd frontend
npm install
npm run dev      # Dev server (port 3000)
npm run build
npm run lint
```

### Docker (full stack)
```bash
docker-compose up --build
```

## Environment Setup

Copy `.env.example` to `.env` in the project root. Key variables:
- `LLM_PROVIDER` / `LLM_MODEL`: Primary LLM (default: `openai` / `gpt-4o-mini`)
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`: Required for cloud LLMs
- `NEXT_PUBLIC_API_URL`: Frontend → backend URL (default: `http://localhost:8000/api`)
- `USE_SQLITE_STORAGE`: Enables persistent sessions/notes — **should be `true` for real use**
- `PHASE2_ROUTING_ENABLED`: Enables multi-agent routing (default: `true`)

## Workflow

### Branching
Use feature branches even when working solo: `feature/short-description`. Keeps `master` clean and makes history readable for open-source contributors.

### Before implementing anything non-trivial
Run `/spec` to write a spec first. Specs live in `docs/specs/YYYY-MM-DD-slug.md`. This gives Claude a clear, referenceable target and prevents scope creep.

### Commit format
```
type: short description
```
Types: `feat` / `fix` / `docs` / `refactor` / `test` / `chore`

### Slash commands (run these in Claude Code)
| Command | When to use |
|---|---|
| `/spec` | Before starting any non-trivial feature |
| `/devlog` | End of a session — captures decisions and gotchas |
| `/changelog` | After completing a feature — updates `[Unreleased]` in CHANGELOG.md |
| `/update-session-handoff` | End of session — keeps SESSION-HANDOFF.md current for next session |

### Session start
Say: `Read docs/SESSION-HANDOFF.md and continue from there.`

## Architecture

### Backend (`backend/app/`)

**API layer** (`routers/`): Six FastAPI routers — books, chat (SSE streaming), sessions, notes, debug, health.

**Orchestration** (`agents/graph.py`): LangGraph pipeline with nodes: `router → query_rewrite → retrieve → agent_prep → stream`. All chat goes through this graph.

**Agents** (`agents/`):
- `router.py` — LLM intent classifier (explain/example/context/quiz/summarize) with keyword fallback
- `tutor.py`, `example_gen.py`, `context_enricher.py`, `quiz_master.py`, `summarizer.py` — one agent per intent
- Summarizer auto-saves output as a note and emits a `note_saved` SSE event

**RAG pipeline** (`rag/`):
- `processor.py` → `chunker.py` (heading-aware, font-size-detected boundaries) → `embeddings.py` → ChromaDB
- `retriever.py`: Hybrid vector + BM25 scoring, configurable `top_k` / `prefetch_multiplier`
- `reranker.py`: Cross-encoder (`ms-marco-MiniLM-L-6-v2`) re-scores candidates

**Services** (`services/`):
- `llm.py` — multi-provider LangChain wrapper (OpenAI → Anthropic → Ollama fallback)
- `database.py` + `storage_provider.py` — transparent JSON/SQLite swap via `USE_SQLITE_STORAGE` flag
- `sessions.py`, `notes.py` — business logic for persistence
- `migrate.py` — SQLite schema migrations

**Config** (`config.py`): Pydantic Settings; all tuning knobs (score_threshold, top_k, reranker toggle, query rewrite toggle) live here.

### Frontend (`frontend/src/`)

**Pages** (`app/`):
- `page.tsx` — home/library (upload + book list)
- `app/book/[bookId]/page.tsx` — main study view (PDF viewer + chat + notes panels)

**Layout**: Three-pane — PDF iframe (left, resizable), chat panel (center/right tab), notes panel (tab). Dark theme via Tailwind CSS v4 custom tokens (`bg-bg`, `text-heading`, `accent`).

**API client** (`lib/api.ts`): All fetch calls to backend, including SSE stream parsing for chat.

### Data Flow (Chat Request)
1. POST `/api/books/{book_id}/chat` → opens SSE stream
2. LangGraph: router classifies intent → LLM rewrites query → hybrid retrieve + rerank → agent streams response
3. SSE events: `token` (streamed text), `sources` (retrieved chunks with relevance labels), `note_saved`, `done`

### Storage Modes
- **JSON mode** (default): In-memory books index + ChromaDB; no persistence across restarts
- **SQLite mode** (`USE_SQLITE_STORAGE=true`): Persistent books, sessions, messages, notes tables in `data/tome.db`

### Tests
Tests live in `backend/tests/`. They use FastAPI `TestClient` and monkeypatching for LLM mocks. The 79 tests cover: LLM router, chat streaming, SSE contract, sessions, session-chat integration, SQLite storage, notes CRUD, and position-aware retrieval.

## Docs
- `docs/SESSION-HANDOFF.md` — current state summary and planned next steps
- `docs/adr/` — architecture decision records
- `docs/specs/` — feature specifications
- `docs/devlog/` — development logs by feature
