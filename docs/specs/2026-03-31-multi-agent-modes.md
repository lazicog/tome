# Spec: Multi-Agent Modes — Learn / Research / Visualize

**Date:** 2026-03-31
**Status:** Approved — ready to implement
**Scope:** Frontend mode selector UI + backend mode-aware orchestrator routing

---

## Problem

The current orchestrator is a single-mode tutor. It is optimised for explanation and guided learning, but
not for two other common study workflows:

- **Research**: "How does this compare to current practice? What has changed since this book was written?
  What do real-world engineers actually do?" — needs web search, broader retrieval, source comparison,
  and an analytical rather than pedagogical tone.
- **Visualize**: "Show me how these concepts relate." — needs diagram generation (future).

Forcing both workflows through the same tutor prompt produces mediocre answers: the tutor adds "Key
concepts to nail down" to a research question and cites pages when the user wanted a web reference.

---

## Goals

1. Add a **Learn / Research / Visualize** mode selector to the chat UI.
2. Backend: route the request through a mode-specific system prompt and tool set.
3. **Learn** = current behaviour, unchanged.
4. **Research** = new mode: analytical, always web-enabled, whole-book retrieval, source attribution.
5. **Visualize** = disabled UI stub only; no backend implementation yet.
6. Mode travels in the `ChatRequest` payload; existing clients default to `"learn"`.

---

## Non-Goals

- Persisting mode per session (state lives in the frontend only; adding it to the DB is future work).
- Automatic mode switching based on intent detection.
- Any Visualize backend implementation in this pass.
- Changes to the eval pipeline or Phoenix instrumentation.

---

## Proposed Design

### Mode Definitions

| Mode | Tone | Tools | Web search | Response format |
|---|---|---|---|---|
| **Learn** | Tutor — explain deeply, quiz, anchor to the book | search_book, get_page_text, save_note, list_notes, update_note, generate_quiz, web_search (if globally enabled) | Optional (settings flag) | Two-part (From the book / More broadly) + Key concepts |
| **Research** | Analyst — compare, synthesise, cite sources | search_book, get_page_text, web_search, list_notes, save_note, update_note | **Always on** (overrides settings flag) | Three-part: **Book says** / **Current practice** / **Differences & caveats** |
| **Visualize** | — | — | — | Disabled stub |

### Research Mode System Prompt (new)

```
You are a research assistant helping a developer go deeper than the book.
Your job: find what the book says, compare it to current practice, and surface differences.

<current_reading>
The user is on page {current_page}.
{page_text_block}
</current_reading>

Tools available:
- search_book: retrieve content from the book. Always call this first.
- get_page_text: read a specific page verbatim.
- web_search: search the web for current documentation, papers, or community consensus.
- list_notes / save_note / update_note: read or save notes when user explicitly requests.

Workflow:
1. Call search_book to ground the answer in the text.
2. Call web_search for current docs, blog posts, or papers on the same topic.
3. Synthesise both into a structured response.

Response format — use this structure for every substantive answer:

---

**Book says** (p.{page})
What this book specifically claims, with page references.

**Current practice**
What practitioners actually do today, based on web sources. Cite URLs inline.

**Where they differ**
Explicit comparison: what has changed, what the book oversimplifies, what holds up well.

**Sources**
- Book: p.{page} — "{chapter}"
- Web: {url} — {one-line summary}

---

Rules:
- Always call search_book before answering.
- Always call web_search unless the question is purely about the current page text.
- Cite every claim. Never state something from memory without a source label.
- If the book and web agree, say so — don't manufacture differences.
- Do not add quiz questions, "Key concepts to nail down", or pedagogical follow-ups.
  This mode is for research, not teaching.
- Be direct and concise. No filler openers.
```

---

## API Changes

### `ChatRequest` schema (`backend/app/schemas.py`)

Add one field with a default:

```python
mode: str = "learn"   # "learn" | "research" | "visualize"
```

Backwards-compatible — existing callers that omit the field get `"learn"`.

### `stream_orchestrated_answer` signature (`backend/app/agents/orchestrator.py`)

```python
async def stream_orchestrated_answer(
    book_id: str,
    message: str,
    history: list[ChatMessage],
    current_page: int | None = None,
    mode: str = "learn",
) -> AsyncGenerator[str | EvalMetadata, None]:
```

Mode is forwarded from `chat.py` → `graph.py` (if routing via `stream_routed_answer`) → `orchestrator.py`.

### Tool set selection by mode

```python
# orchestrator.py
def _get_tools(mode, book_id, current_page, retrieved_chunks, pending_notes, web_sources):
    tools = build_tools(book_id, current_page, retrieved_chunks, pending_notes, web_sources)
    if mode == "research":
        # Ensure web_search is always included in research mode
        if not any(t.name == "web_search" for t in tools):
            tools = build_tools_with_web(...)  # see below
        # Drop generate_quiz from research mode
        tools = [t for t in tools if t.name != "generate_quiz"]
    return tools
```

Simplest implementation: `build_tools` already adds `web_search` when `settings.web_search_enabled`.
For research mode, pass a flag that forces web search regardless of the settings flag.

Add `force_web_search: bool = False` param to `build_tools()`:

```python
def build_tools(book_id, current_page, retrieved_chunks, pending_notes, web_sources,
                *, force_web_search: bool = False) -> list:
    ...
    if settings.web_search_enabled or force_web_search:
        # add web_search tool
```

### System prompt selection

```python
def _build_system_prompt(current_page, page_text, mode="learn") -> str:
    if mode == "research":
        return RESEARCH_SYSTEM_PROMPT.format(...)
    return LEARN_SYSTEM_PROMPT.format(...)   # existing prompt, renamed
```

---

## Frontend Changes

### Mode selector component

Location: chat panel header — above the sessions row.

UI: Three compact icon+label buttons in a pill group.

```
[ 📖 Learn ]  [ 🔍 Research ]  [ 🔮 Visualize ↗ ]
```

- Active mode: sage-tinted border + text (`#6B9B6B`)
- Inactive: `#303030` border, `#737373` text
- Visualize button: disabled, `opacity-40`, tooltip "Coming soon"
- State: `useState<"learn" | "research">("learn")` in the book page component
- Persists within the page session (resets on page reload — acceptable for now)

### Chat payload

```typescript
// lib/api.ts — sendChatMessage
body: JSON.stringify({
  message,
  session_id: sessionId,
  current_page: currentPage,
  mode,            // new field
})
```

### Visual differentiation in chat

When mode is `"research"`, show a small badge on assistant messages:

```
[Research]  ← small sage pill badge, 9px font
```

This lets the user know the response came from the research agent.

---

## File Plan

| File | Change |
|---|---|
| `backend/app/schemas.py` | Add `mode: str = "learn"` to `ChatRequest` |
| `backend/app/agents/orchestrator.py` | Add `mode` param, `_build_system_prompt` dispatch, `RESEARCH_SYSTEM_PROMPT` constant |
| `backend/app/agents/tools.py` | Add `force_web_search` param to `build_tools()` |
| `backend/app/api/routes/chat.py` | Forward `payload.mode` into `stream_orchestrated_answer` |
| `backend/app/api/routes/graph.py` (if exists) | Forward mode if `stream_routed_answer` wraps orchestrator |
| `frontend/src/app/book/[bookId]/page.tsx` | Add `mode` state, `ModeSelector` component, pass mode in chat payload, add Research badge on messages |
| `frontend/src/lib/api.ts` | Add `mode` to chat request type and fetch call |

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Research mode always calling web_search adds latency | Acceptable — user opted in. Show "Searching web…" thinking label as before. |
| Research prompt too verbose for simple lookups | Add single-paragraph fallback: if question is clearly a page/definition lookup, skip the three-part format |
| `force_web_search=True` when Tavily key missing | Falls back to DuckDuckGo — already implemented in `_do_web_search()` |
| Mode badge clutters the chat | Badge is minimal (9px pill) and only on research responses |

---

## Test Plan

1. `pytest tests/test_router.py` — no regression (mode defaults to "learn")
2. New test `tests/test_modes.py`:
   - `test_learn_mode_uses_current_system_prompt` — system prompt contains "From the book"
   - `test_research_mode_uses_research_prompt` — system prompt contains "Book says"
   - `test_research_mode_forces_web_search_tool` — `web_search` in tool list even when `settings.web_search_enabled=False`
   - `test_research_mode_excludes_generate_quiz` — `generate_quiz` not in tool list
   - `test_chat_request_defaults_mode_to_learn` — schema default
3. `npm run build` — no TypeScript errors on frontend

---

## Implementation Checklist

- [ ] `schemas.py`: add `mode` field
- [ ] `tools.py`: add `force_web_search` param
- [ ] `orchestrator.py`: add mode param, research prompt, mode-based tool selection
- [ ] `chat.py` / `graph.py`: forward mode
- [ ] `api.ts`: add mode to request type and payload
- [ ] `page.tsx`: add mode state, ModeSelector UI, Research badge
- [ ] `tests/test_modes.py`: write 5 new tests
- [ ] All existing tests still pass
