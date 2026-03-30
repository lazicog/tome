# Devlog: Orchestrator Overhaul + PDF Viewer

**Date:** 2026-03-30
**Session focus:** Replace 5-agent routing system with single tool-calling orchestrator; replace iframe PDF viewer with react-pdf canvas renderer; LLM-suggested note titles

---

## What shipped

### 1. Single orchestrator agent (replaces 5-agent LangGraph)

**Problem:** The multi-agent routing architecture had fundamental limitations:
- Router classified intent before retrieval, so it couldn't adapt to what was actually found
- Agents had no tools — they only saw whatever RAG happened to retrieve
- No way to combine intents (e.g. "explain and save a note")
- Auto-save for summarize was a hack in `chat.py`, not part of the agent
- 5 single-file agents that were each just a prompt constant

**Decision:** Replace the LangGraph pipeline with a single tool-calling orchestrator. The orchestrator decides what it needs (retrieval, page text, note-saving, quiz generation) by calling tools, rather than being pre-classified by a router.

**New architecture:**
```
User message + current_page
        │
        ▼
OrchestratorAgent (streaming, tool-enabled)
        ├── search_book(query, whole_book?)   → semantic chunks
        ├── get_page_text(page_number)         → verbatim page text
        ├── save_note(title, content, tags)    → persisted note + SSE
        └── generate_quiz(topic)               → quiz questions
        ▼
Streamed tokens → sources SSE → done
```

**Key implementation details:**

The orchestrator uses a streaming tool-call loop:
```python
for iteration in range(MAX_TOOL_ITERATIONS):
    chunk_buffer = []
    async for chunk in llm_with_tools.astream(messages):
        chunk_buffer.append(chunk)
        text = _extract_text(chunk.content)
        if text:
            yield _sse_event("token", text)  # stream final answer tokens in real-time

    full_response = reduce(operator.add, chunk_buffer)
    messages.append(full_response)

    if not full_response.tool_calls:
        break  # Done

    for tc in full_response.tool_calls:
        yield _sse_event("thinking", thinking_label(tc["name"]))
        result = await tool_map[tc["name"]].ainvoke(tc["args"])
        messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
```

This gives us:
- Real-time streaming when there are no tool calls (common case for follow-up questions)
- `thinking` SSE events during tool execution ("Searching book…", "Reading page…")
- Correct handling of multi-tool-call responses

**System prompt** injects the current page verbatim text upfront so the agent always knows what the user is reading:
```xml
<current_reading>
The user is on page {current_page}.
Page text:
{page_text}
</current_reading>
```

**`page_extractor.py`** — new module that uses pdfplumber to extract verbatim page text for injection into the prompt. Handles missing files, out-of-range pages, and encoding issues gracefully.

**Web search tool** — opt-in via `WEB_SEARCH_ENABLED=true` in `.env`. Uses Tavily if `TAVILY_API_KEY` is set, falls back to DuckDuckGo (no key needed). Web sources emitted as `web_sources` SSE event.

**Files deleted:** `router.py`, `example_gen.py`, `context_enricher.py`, `quiz_master.py`, `summarizer.py` — these were each just a prompt string constant with no logic.

**`graph.py`** reduced to a 6-line thin wrapper for API compatibility:
```python
async def stream_routed_answer(book_id, message, history, current_page=None):
    async for event in stream_orchestrated_answer(book_id, message, history, current_page):
        yield event
```

**`chat.py`** simplified — removed `_note_aware_stream` (orchestrator handles note-saving via `save_note` tool) and the `phase2_routing_enabled` fallback path.

**Test impact:** Updated `test_router.py` to test tools module instead of deleted router. Updated `test_chat_stream_integration.py` to remove `agent` SSE event assertions (no longer emitted) and `stream_tutor_answer` fallback test. All 58 tests pass.

---

### 2. react-pdf canvas PDF viewer (replaces iframe)

**Problem:** The iframe PDF viewer was browser-native but had no integration — we couldn't track which page the user was on, navigate programmatically, or control zoom/keyboard.

**Decision:** Replace with react-pdf v7 (not v9 — see below) for canvas rendering with full control.

**Why react-pdf v7 not v9:**
- react-pdf v9 uses pdfjs-dist v4 which is ESM-only
- Next.js 15 webpack has a known incompatibility with pdfjs-dist v4 `.mjs` files
- react-pdf v7 uses pdfjs-dist v3 (CommonJS), works cleanly

**Key features implemented:**
- Continuous scroll: all pages rendered in one scrollable div (not single-page flip)
- `IntersectionObserver` tracks which page is most visible → `onPageChange` callback
- `ResizeObserver` measures container width → fit-to-width zoom
- Bottom toolbar: prev/next page, page number input, zoom in/out
- Text selection and annotation layers enabled (`renderTextLayer`, `renderAnnotationLayer`)
- `next/dynamic` with `ssr: false` to prevent SSR issues

**Keyboard navigation** — required solving two interacting problems:

*Problem 1: Smooth scroll jank*
Initial approach used `scrollBy({ behavior: "smooth" })` on keydown repeat — caused visible stutter. Solution: `requestAnimationFrame` loop with a `keysHeld` Set. ArrowUp/Down scroll 20px per frame; loop runs while key is held, stops on keyup.

*Problem 2: rAF loop teardown*
The keyboard effect had `pageNum` in its dep array. Every `IntersectionObserver` update (which fires constantly while scrolling) changed `pageNum` state → triggered effect teardown → cancelled the rAF loop mid-scroll. Solution: Added `pageNumRef`/`numPagesRef` refs that mirror state, keyboard effect only depends on `[scrollToPage]` (stable via `useCallback`).

*Problem 3: Scroll conflicts*
ArrowLeft/Right used `scrollIntoView({ behavior: "smooth" })` which conflicted with the rAF loop writing `scrollTop` directly. Solution: Page jumps use instant `container.scrollTop = el.offsetTop - 16` — only one mechanism ever writes `scrollTop`.

**`next.config.ts` change:**
```ts
webpack: (config) => {
  config.resolve.alias.canvas = false;  // required for pdfjs in webpack
  return config;
}
```

---

### 3. LLM-suggested note titles

When user clicks "Save as note" on an assistant message, the app now:
1. Opens a dialog (not saves immediately)
2. Calls `POST /api/notes/suggest-title` with the message content
3. LLM generates a 5-8 word title
4. User sees title pre-filled and can edit before saving
5. Enter key confirms, Escape cancels

The title suggestion uses a minimal LLM call with a short focused prompt ("Generate a concise title (5-8 words) for this note. Reply with just the title, no quotes or punctuation.")

---

### 4. Frontend UX improvements

- **`/` keyboard shortcut** focuses the chat textarea from anywhere on the page (skips input/textarea elements)
- **`thinking` label** appears below typing indicator while tools execute ("Searching book…", "Reading page…", "Saving note…")
- **Web sources section** — collapsible `<details>` below book sources, shows URL + snippet for each web result
- **No agent label** — removed the "Tutor" / "Summary" / "Example" labels from message bubbles (no longer meaningful with a single orchestrator)
- **Toast message** simplified: "Note saved" (was "Study note saved automatically")

---

## Gotchas

- **react-pdf v7 worker URL** must use `.min.js` (not `.min.mjs`): `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`
- **Streaming tool calls with LangChain**: when the LLM returns tool calls, `chunk.content` is typically empty — so token streaming in the loop emits nothing during tool-call rounds. The final answer round emits real tokens. This is correct behavior, not a bug.
- **`operator.add` on AIMessageChunk**: LangChain's message chunks support `__add__` for merging. `reduce(operator.add, chunk_buffer)` gives the full AIMessage with all tool calls assembled.
- **Web search disabled by default**: `WEB_SEARCH_ENABLED=false` in `.env`. Enabling it without a Tavily key falls back to DuckDuckGo which is free but rate-limited.

---

## Test count

| File | Tests |
|---|---|
| `test_chat_stream_integration.py` | 8 |
| `test_router.py` (now tests tools module) | 5 |
| `test_session_chat_integration.py` | 5 |
| `test_sessions.py` | 6 |
| `test_notes.py` | 10 |
| `test_sse_contract.py` | 4 |
| `test_storage_db.py` | 5 |
| `test_position_filter.py` | 15 |
| **Total** | **58** |
