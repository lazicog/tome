# Devlog: Multi-Agent Modes, Model Picker, and Color Pass

**Date:** 2026-04-02
**Features:** Multi-agent modes (Learn/Research), per-request model picker, unified sage accent

---

## What was built

### 1. Unified sage accent color (`#6B9B6B`)

Replaced the previous two-color split (dark green fills + amber text) with a single muted sage across the entire app.

- `globals.css`: `--color-accent`, `--primary`, `--ring` all updated; replaced all `rgba(2,53,2)` and `#D97706` with sage equivalents
- `layout.tsx`: Added a `position: fixed` 1px top bar (`rgba(107,155,107,0.35)`, `z-index: 9999`) — a barely-visible brand stripe on every page
- `page.tsx` (home): Fixed 4 leftover `rgba(99,102,241,…)` indigo tints on icon containers and search input focus ring
- `PdfViewer.tsx`: Fixed page input focus border
- `book/[bookId]/page.tsx`: Sage tint on FileText icons in source cards (`rgba(107,155,107,0.6)`); progress rail counter text (`rgba(107,155,107,0.5)`)

### 2. Multi-agent modes — Learn / Research

Added a **mode selector** above the sessions row in the chat panel.

**Learn** (default): existing tutor behaviour — explains concepts, gives examples, quizzes, saves notes, "Key concepts to nail down" follow-up section.

**Research** (new): analytical mode always enabled with web search. Uses a separate `RESEARCH_SYSTEM_PROMPT` with a three-part output format:
- **Book says** — what the book claims, with page references
- **Current practice** — web sources, URL citations
- **Where they differ** — explicit comparison, caveats, what holds up

**Visualize**: disabled stub with "Coming soon" tooltip.

Backend changes:
- `schemas.py`: `mode: str = "learn"` on `ChatRequest`
- `agents/tools.py`: `force_web_search: bool = False` param — research mode forces web search regardless of `WEB_SEARCH_ENABLED` flag
- `agents/orchestrator.py`: `RESEARCH_SYSTEM_PROMPT` constant; `_build_system_prompt(mode=)` dispatch; research mode filters out `generate_quiz` tool
- `chat.py` / `graph.py`: mode forwarded through the entire call stack
- `frontend/src/lib/api.ts`: `ChatMode = "learn" | "research"` type
- `frontend/.../page.tsx`: `ModeSelector` component; mode sent in chat payload; assistant messages tagged with `mode`; "Research" pill badge on research responses

Tests: `tests/test_modes.py` — 7 tests covering prompt dispatch, tool inclusion/exclusion, schema defaults, and integration with chat route.

### 3. Per-request model picker

Users can now select the LLM per request from a dropdown next to the mode buttons.

Available models defined in `config.py` as `AVAILABLE_MODELS`:
- GPT-5.4 mini (default)
- GPT-5.4
- Claude Haiku
- Claude Sonnet
- Claude Opus

The `GET /api/models` endpoint returns only the models whose provider API key is configured — no broken options shown.

Backend changes:
- `config.py`: `AVAILABLE_MODELS` list
- `api/routes/models.py`: new router — `GET /api/models`, filtered by `openai_api_key` / `anthropic_api_key`, marks default
- `main.py`: models router registered
- `schemas.py`: `model_id: str | None = None` on `ChatRequest`
- `orchestrator.py`: `_resolve_model(model_id)` — looks up provider from `AVAILABLE_MODELS`, calls `get_chat_model(provider, model_id)`, falls back to default chain if unknown
- `graph.py` / `chat.py`: `model_id` forwarded through the stack

Frontend changes:
- `api.ts`: `Model` type + `listModels()` function
- `page.tsx`: model state initialised from `localStorage` (`tome_model_id`); falls back to server default; `<select>` dropdown in the mode selector bar, right-aligned; `model_id` sent with every chat POST; small dim label badge on assistant messages showing which model responded

Tests: `tests/test_models_endpoint.py` — 6 tests covering response shape, provider filtering, default marking.

---

## Test count

83 tests, all passing (up from 63 after adding test_modes.py and test_models_endpoint.py).

---

## Decisions

- **Research web search always-on**: `force_web_search=True` overrides the global `WEB_SEARCH_ENABLED` flag. Research mode is explicitly opted into — users who pick it expect web results.
- **Model badge always shown** (not just for non-default): makes the UI transparent about which model answered. Small enough not to be noise.
- **localStorage, not SQLite**: model preference is personal and cross-book; no need for per-session DB storage.
- **Static AVAILABLE_MODELS list**: avoids dynamic enumeration complexity. Ollama users can extend the list manually later.
