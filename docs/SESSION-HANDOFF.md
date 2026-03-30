# Tome Session Handoff

Use this file as the startup context when resuming work with the agent.

## How to resume

At the start of the next session, say:

`Read docs/SESSION-HANDOFF.md and continue from there.`

Devlogs for context:
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
- Tools: search_book, get_page_text, save_note, generate_quiz, web_search (opt-in)
- Current page text injected verbatim into system prompt
- thinking SSE events during tool execution; web_sources SSE for web results
- LLM-suggested note titles with editable dialog before saving
- Deleted: router.py, example_gen.py, context_enricher.py, quiz_master.py, summarizer.py
- Test count: 58 (all passing)
- Devlog: docs/devlog/2026-03-30-orchestrator-pdf-viewer.md

### react-pdf PDF Viewer — COMPLETE (2026-03-30)
- Replaced iframe with react-pdf v7 canvas renderer
- Continuous scroll, IntersectionObserver page tracking, fit-to-width zoom
- rAF-loop keyboard scroll (ArrowUp/Down), instant page jumps (ArrowLeft/Right)
- Bottom toolbar: page nav, page number input, zoom controls
- Text selection + annotation layers; / shortcut focuses chat input

### Phoenix + Eval Pipeline — IN PROGRESS (spec written, implementation next)
- Spec: docs/specs/2026-03-30-phoenix-eval-pipeline.md
- No Docker needed — Phoenix runs as: python -m phoenix.server.main
- Plan: Phoenix OTel instrumentation + LLM-as-judge evals stored in SQLite

---

## Immediate next steps

Implement Phoenix + eval pipeline per spec at docs/specs/2026-03-30-phoenix-eval-pipeline.md:

1. Add phoenix_enabled / phoenix_endpoint to config.py
2. Wire LangChainInstrumentor in main.py lifespan
3. Add evals table to database.py
4. Create services/evals.py (CRUD)
5. Create agents/evaluator.py (LLM-as-judge)
6. Extend orchestrator to return eval metadata
7. Fire eval task in chat.py after stream
8. Add /api/debug/evals endpoint
9. Write tests

---

## Run without Docker

```
# Backend
cd backend
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000

# Phoenix (when PHOENIX_ENABLED=true in .env)
cd backend
.venv/Scripts/python -m phoenix.server.main
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
- Web search: Tavily primary, DuckDuckGo fallback, opt-in via WEB_SEARCH_ENABLED=true
- Solo workflow: Direct commits to master

---

## Known gotchas

- Port conflict: netstat -ano | findstr :8000 -> taskkill /PID <PID> /F
- localhost vs 127.0.0.1 mismatch triggers CORS errors
- PowerShell: use ; not && between commands
- react-pdf v7 worker URL must be .min.js not .min.mjs
- Existing books need re-ingest after chunker changes
- LLM tool-calling requires function-calling capable model (GPT-4o-mini, Claude 3.x)
- WEB_SEARCH_ENABLED=false by default

---

## Test suite

58 tests, all passing.
Run: cd backend && .venv/Scripts/python -m pytest -q

| File | Tests |
|---|---|
| test_chat_stream_integration.py | 8 |
| test_router.py | 5 |
| test_session_chat_integration.py | 5 |
| test_sessions.py | 6 |
| test_notes.py | 10 |
| test_sse_contract.py | 4 |
| test_storage_db.py | 5 |
| test_position_filter.py | 15 |
