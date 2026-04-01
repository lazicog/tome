# Spec: Visualize Mode

**Date:** 2026-04-02
**Status:** Approved — ready to implement

## Context

The app has two working chat modes — Learn (tutor) and Research (analytical, web-grounded). The "Visualize" button has been in the ModeSelector since Research shipped, disabled with a "Coming soon" tooltip.

Visualize fills a gap: neither Learn nor Research makes structural relationships *visible*. When reading about microservice patterns, class hierarchies, or protocol flows, a diagram often conveys the structure faster than any explanation. The LLM can generate Mermaid syntax reliably (trained on millions of examples). The frontend already renders markdown via ReactMarkdown. The only additions needed are a system prompt, a tool filter, and a custom Mermaid code-block renderer.

**Approach: Mermaid.js text-based diagrams** — the LLM outputs a Mermaid fenced code block in the token stream (no new SSE events, no new backend routes, no DB changes). The frontend intercepts `mermaid`-language code blocks in ReactMarkdown and renders them as SVG diagrams.

---

## Response format

The `VISUALIZE_SYSTEM_PROMPT` instructs the LLM to always produce exactly:

```
[One sentence: what this diagram shows and why it's useful.]

```mermaid
[diagram markup]
```

**Key relationships**
- [insight 1]
- [insight 2]
- [insight 3]
```

LLM picks diagram type based on content:
- `mindmap` — concept hierarchies, chapter overviews
- `flowchart LR` — processes, algorithms, decision trees
- `graph LR` — entity relationships, dependencies
- `sequenceDiagram` — request/response cycles, step-by-step interactions

Node label limit: 3–5 words. Diagram size: 6–16 nodes. No web search — book-grounded only.

---

## Backend changes

### `backend/app/agents/orchestrator.py`

**1. Add `VISUALIZE_SYSTEM_PROMPT` constant** (after `RESEARCH_SYSTEM_PROMPT`):

```python
VISUALIZE_SYSTEM_PROMPT = """\
You are a visual learning companion for technical books.
Your job is to turn book concepts into clear, accurate Mermaid diagrams that reveal structure the text alone cannot.

<current_reading>
The user is on page {current_page}.
{page_text_block}
</current_reading>

You have tools:
- **search_book**: Search the book semantically. Always call this first to ground the diagram in the text.
- **get_page_text**: Read a specific page verbatim. Use when you need exact names, code, or enumerated steps.

Diagram type selection — choose the most appropriate type for the content:
- **mindmap** — concept hierarchies, chapter overviews, taxonomy of ideas
- **flowchart LR** — processes, algorithms, decision trees, data flows
- **graph LR** — entity relationships, dependencies, bidirectional connections
- **sequenceDiagram** — protocol flows, request/response cycles, step-by-step interactions

Response format — always use exactly this three-part structure:

[One sentence: what this diagram shows and why it is useful for understanding the topic.]

\`\`\`mermaid
[diagram markup here]
\`\`\`

**Key relationships**
- [relationship or insight 1 — one sentence]
- [relationship or insight 2 — one sentence]
- [relationship or insight 3 — one sentence]

Rules:
- Always call search_book before generating a diagram.
- Ground every node and edge in book content — do not invent concepts the book does not cover.
- Use short node labels (3–5 words maximum).
- For mindmap: use only indentation, no brackets or parentheses on root node.
- For flowchart and graph: use LR direction unless the concept is clearly hierarchical (use TD then).
- Keep diagrams readable: 6–16 nodes. If the concept is too large, scope it to the current page's sub-topic.
- Do not add quiz questions, key concepts to nail down, or pedagogical follow-ups.
- Do not use web_search. Diagrams must be grounded in the book only.
- Be direct. No filler openers.
"""
```

**2. Add `elif` branch in `_build_system_prompt`** (after the `if mode == "research"` block):

```python
elif mode == "visualize":
    return VISUALIZE_SYSTEM_PROMPT.format(
        current_page=current_page or "unknown",
        page_text_block=page_text_block,
    )
```

**3. Add tool filter in `stream_orchestrated_answer`** (after the research filter):

```python
if mode == "visualize":
    tools = [t for t in tools if t.name in ("search_book", "get_page_text")]
```

Visualize gets 2 tools only: `search_book` + `get_page_text`. No quiz, no notes, no web search.

---

## Frontend changes

### `frontend/src/lib/api.ts`
```typescript
// Before
export type ChatMode = "learn" | "research";
// After
export type ChatMode = "learn" | "research" | "visualize";
```

### `frontend/src/app/book/[bookId]/page.tsx`

**1. ModeSelector — replace disabled stub:**

Change the mapped array from `["learn", "research"]` to `["learn", "research", "visualize"]`. Remove the separate disabled `<button>` for Visualize entirely — it's now covered by the `.map()` loop.

Update the label ternary:
```tsx
// Before
{m === "learn" ? "Learn" : "Research"}
// After
{m === "learn" ? "Learn" : m === "research" ? "Research" : "Visualize"}
```

The active sage styling (`#6B9B6B` border/bg/text) already uses `mode === m`, so Visualize gets it automatically.

**2. MessageBubble — Visualize badge** (add after the Research badge block):
```tsx
{mode === "visualize" && (
  <span
    className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium"
    style={{ background: "rgba(107,155,107,0.12)", color: "#6B9B6B" }}
  >
    Visualize
  </span>
)}
```

**3. Dynamic import for MermaidDiagram** (alongside existing PdfViewer dynamic import):
```tsx
const MermaidDiagram = dynamic(() => import("@/components/MermaidDiagram"), { ssr: false });
```

**4. ReactMarkdown `components` prop** in `MessageBubble` (replace bare `<ReactMarkdown>` call):
```tsx
<ReactMarkdown
  remarkPlugins={[remarkGfm]}
  components={{
    code({ className, children, ...props }) {
      const language = /language-(\w+)/.exec(className ?? "")?.[1];
      if (language === "mermaid") {
        return <MermaidDiagram chart={String(children).trim()} />;
      }
      return <code className={className} {...props}>{children}</code>;
    },
  }}
>
  {content}
</ReactMarkdown>
```

### `frontend/src/components/MermaidDiagram.tsx` (NEW)

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  themeVariables: {
    darkMode: true,
    background: "#151515",
    primaryColor: "rgba(107,155,107,0.18)",
    primaryTextColor: "#F0F0F0",
    primaryBorderColor: "#303030",
    lineColor: "#6B9B6B",
    secondaryColor: "#1C1C1C",
    tertiaryColor: "#0E0E0E",
    edgeLabelBackground: "#151515",
    nodeTextColor: "#F0F0F0",
  },
});

let _counter = 0;

export default function MermaidDiagram({ chart }: { chart: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const idRef = useRef(`mermaid-${++_counter}`);

  useEffect(() => {
    if (!containerRef.current) return;
    setError(null);
    mermaid.render(idRef.current, chart)
      .then(({ svg }) => {
        if (containerRef.current) containerRef.current.innerHTML = svg;
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
      });
  }, [chart]);

  if (error) {
    return (
      <div className="my-2 rounded-lg border px-3 py-2 text-xs font-mono overflow-x-auto"
        style={{ background: "#0E0E0E", borderColor: "#303030" }}>
        <span style={{ color: "#EF4444" }}>Diagram render error: </span>{error}
        <pre className="mt-1 text-[10px]" style={{ color: "#737373" }}>{chart}</pre>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="my-3 overflow-x-auto rounded-lg"
      style={{ background: "#0E0E0E", border: "1px solid #242424", padding: "1rem" }} />
  );
}
```

Key design notes:
- `mermaid.initialize` at module scope with `startOnLoad: false` — prevents DOM scanning on import
- `_counter` is module-level — each instance gets a stable unique ID via `useRef` to prevent collisions when multiple diagrams exist simultaneously
- Error fallback shows raw Mermaid source — user always sees something even on LLM syntax errors
- `overflow-x: auto` on container — sequenceDiagrams can be wider than the chat panel

### `frontend/package.json`
```
npm install mermaid
```

---

## Files to modify

| File | Change |
|---|---|
| `backend/app/agents/orchestrator.py` | `VISUALIZE_SYSTEM_PROMPT`, `_build_system_prompt` dispatch, tool filter |
| `frontend/src/lib/api.ts` | Add `"visualize"` to `ChatMode` |
| `frontend/src/app/book/[bookId]/page.tsx` | Enable ModeSelector button, Visualize badge, MermaidDiagram dynamic import + ReactMarkdown components prop |
| `frontend/src/components/MermaidDiagram.tsx` | NEW — Mermaid renderer component |
| `frontend/package.json` | `mermaid` dependency via npm install |

No changes to: `schemas.py`, `chat.py`, `graph.py`, `tools.py`, `globals.css`, any SSE event types, database.

---

## Tests

**`backend/tests/test_orchestrator_visualize.py`** (new, 4 tests):
1. `test_visualize_system_prompt_used` — `_build_system_prompt(mode="visualize")` contains Mermaid instructions, not "Key concepts to nail down"
2. `test_visualize_tool_filter` — only `search_book` and `get_page_text` in tool list for visualize mode
3. `test_learn_not_regressed` — `_build_system_prompt(mode="learn")` still returns learn prompt
4. `test_research_not_regressed` — `_build_system_prompt(mode="research")` still returns research prompt

**Frontend build**: `npm run build` — no TypeScript errors. The `ssr: false` on the dynamic import prevents SSR crashes from Mermaid's DOM dependency.

---

## Implementation checklist

- [ ] `orchestrator.py`: add `VISUALIZE_SYSTEM_PROMPT` constant
- [ ] `orchestrator.py`: add `elif mode == "visualize"` in `_build_system_prompt`
- [ ] `orchestrator.py`: add visualize tool filter in `stream_orchestrated_answer`
- [ ] `api.ts`: add `"visualize"` to `ChatMode`
- [ ] `npm install mermaid` in frontend
- [ ] `MermaidDiagram.tsx`: create new component
- [ ] `page.tsx`: add `MermaidDiagram` dynamic import
- [ ] `page.tsx`: enable Visualize in ModeSelector array, remove disabled stub, update label ternary
- [ ] `page.tsx`: add Visualize badge in `MessageBubble`
- [ ] `page.tsx`: add `components` prop to `ReactMarkdown`
- [ ] `test_orchestrator_visualize.py`: write 4 tests
- [ ] All 83 existing tests still pass
- [ ] `npm run build` clean

---

## Manual QA checklist

- [ ] Visualize button activates with sage styling (`#6B9B6B`), no "Coming soon" tooltip
- [ ] Chat response contains: framing sentence + Mermaid diagram + Key relationships
- [ ] Diagram renders as SVG (not raw code block)
- [ ] Wide diagrams (`sequenceDiagram`) scroll horizontally
- [ ] Invalid Mermaid markup shows error fallback with raw source
- [ ] `search_book` thinking indicator fires ("Searching book…")
- [ ] Sources panel populates with book chunks
- [ ] No `web_search` or `generate_quiz` tool calls in Visualize responses
- [ ] Learn and Research modes unaffected
- [ ] Non-mermaid code blocks in other modes still render as `<code>`
