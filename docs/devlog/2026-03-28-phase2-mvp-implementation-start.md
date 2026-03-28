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
- Added routing visibility and behavior tuning pass after manual chat checks:
  - backend now emits explicit `agent` SSE event for routed and fallback tutor flows
  - frontend chat UI now renders routed assistant label from stream events
  - refined prompts for Example Generator and Context Enricher for stronger role separation
- Added regression hardening after manual routed chat validation:
  - router now classifies based on the current user query (not prior chat turns)
  - context intent matching now takes precedence over example intent matching
  - expanded tests for router phrase variants and SSE `agent` / `done` event contract
- Added API-level routed chat integration coverage:
  - new test validates stream event ordering contract (`agent` -> `token` -> `sources` -> `done`)
  - test patches route dependencies to isolate API behavior without external LLM/network calls
- Added API-level fallback chat integration coverage:
  - new test validates Tutor stream ordering when `phase2_routing_enabled=false`
  - confirms fallback path keeps the same SSE contract ordering
- Added API-level upload lifecycle integration coverage:
  - new test exercises upload -> ready status -> routed chat stream flow
  - test uses mocked storage/processing + routed stream dependencies for deterministic behavior
- Improved chat source UX on frontend:
  - parse `sources` SSE payload into structured typed entries
  - render source cards with chapter/section/page numbers and retrieval score
  - clear prior source list at the start of each new user turn
- Added multi-agent parallel development assets:
  - worktree collaboration playbook at `docs/workflows/multi-agent-worktree-playbook.md`
  - project skills for `multi-agent-coordinator`, `worktree-feature-builder`, `pr-review-guardian`, and `worktree-integration-manager`
  - role-based templates/checklists for handoff, review findings, and merge integration logs

## Key decisions made

- Use deterministic keyword-based routing for Phase 2 MVP intent classification (`explain`, `example`, `context`) to avoid adding model-classifier latency/cost in the first pass.
- Keep SSE event framing stable and explicit (`agent`, `token`, `sources`, `done`) for frontend compatibility.
- Route fallback remains Tutor behavior (`explain`) when intent is ambiguous.

## Issues / Gotchas

- Latest `langgraph` (1.x) upgraded `langchain-core` to 1.x, which conflicted with installed `langchain-openai/anthropic/ollama` packages.
- Resolved by pinning a compatible `langgraph` version (`0.3.34`) and restoring `langchain-core` to `0.3.76`.

## Next steps

- Run a short end-to-end check for mixed-turn conversations (example -> context -> explain) in the UI.
- Continue remaining Phase 2 checklist items from the approved spec.
