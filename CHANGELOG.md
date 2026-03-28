# Changelog

All notable changes to HelpMeLearn will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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

### Changed
- Frontend now auto-refreshes book status while ingestion is in progress and only enables chat links once a book is ready
- SSE parsing in chat page now supports multi-line `data:` frames for better stream compatibility
- Backend streaming utility now supports prompt-driven routed responses while preserving SSE event contract
- Chat UI now displays routed assistant label (`Tutor`, `Example Agent`, `Context Enricher`) from backend stream events
- Example Generator and Context Enricher prompts are tuned for clearer role-specific behavior
- Chat UI now renders structured source cards (chapter/section/pages/score) instead of raw source JSON

### Fixed
- Upload endpoint now enforces max upload size and rejects empty uploads with clear errors
- ChromaDB metadata serialization now stores scalar-safe values and reconstructs `page_numbers` on retrieval
- CORS defaults now allow both `http://localhost:3000` and `http://127.0.0.1:3000` for local development
- Routed and fallback chat paths now emit explicit `agent` stream events so routing is visible to the user
- Router no longer overweights prior history terms (for example, earlier "code example") when classifying the current user turn
