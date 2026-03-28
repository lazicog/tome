# 2026-03-28: Phase 2 MVP Implementation Start

## What was done

- Began implementation from `docs/specs/2026-03-28-phase2-mvp-router-3-agents.md`
- Added intent router module:
  - `backend/app/agents/router.py`
- Added specialized agent prompt modules:
  - `backend/app/agents/example_gen.py`
  - `backend/app/agents/context_enricher.py`
- Added LangGraph orchestration:
  - `backend/app/agents/graph.py`
  - shared typed state, retrieval node, router node, and conditional prep nodes
- Updated chat route to use routed graph flow instead of Tutor-only flow:
  - `backend/app/api/routes/chat.py`
- Extended tutor utilities to support generic prompt streaming:
  - `backend/app/agents/tutor.py`
- Added `langgraph` dependency to backend requirements:
  - `backend/requirements.txt`

## Key decisions made

- Use deterministic keyword-based routing for Phase 2 MVP intent classification (`explain`, `example`, `context`) to avoid adding model-classifier latency/cost in the first pass.
- Keep current SSE contract stable (`token`, `sources`, `done`) to avoid frontend contract breaks.
- Route fallback remains Tutor behavior (`explain`) when intent is ambiguous.

## Issues / Gotchas

- Latest `langgraph` (1.x) upgraded `langchain-core` to 1.x, which conflicted with installed `langchain-openai/anthropic/ollama` packages.
- Resolved by pinning a compatible `langgraph` version (`0.3.34`) and restoring `langchain-core` to `0.3.76`.

## Next steps

- Implement/verify full routing behavior in runtime path with local integration checks:
  - `example` query routes to Example node prompt
  - `context` query routes to Context node prompt
  - default routes to Tutor
- Add tests for routing classification and SSE event contract.
- Continue remaining Phase 2 checklist items from the approved spec.
