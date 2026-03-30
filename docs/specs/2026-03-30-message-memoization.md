# Spec: Chat Message Rendering Memoization

**Date**: 2026-03-30
**Status**: Approved
**File affected**: `frontend/src/app/book/[bookId]/page.tsx`

---

## Problem

When the AI streams a response token-by-token, every token triggers `setMessages(...)` which replaces the messages array reference. React re-renders **all** message bubbles in the list on every token — including completed, stable messages from earlier in the conversation. Each re-render forces `ReactMarkdown` to re-parse and re-diff the output, causing visible flicker in the chat UI.

The root cause is that the message list is rendered inline in `BookPage` with no memoization boundary:
```tsx
messages.map((m, i) => (
  <div key={i}>...</div>  // re-executes for every message on every token
))
```

---

## Goal

Only the actively-streaming message (always the last one) should re-render on each token. All completed messages should be skipped by React's reconciler.

---

## Non-Goals

- State grouping / reducer refactor (separate concern)
- Moving `MessageBubble` to its own file
- Memoizing `NotesDrawer`, `PdfViewer`, or other major components
- Changing the SSE streaming logic

---

## Design

### Extract `MessageBubble` as a `memo` component

Define `MessageBubble` in the same file (above `BookPage`), wrapping it with `React.memo`. React's shallow prop equality check will bail out for any bubble whose props haven't changed since the last render.

**Props interface:**
```tsx
interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  isLast: boolean;
  thinkingLabel: string;      // only relevant when isLast=true
  waitingForFirst: boolean;   // only relevant when isLast=true
  sending: boolean;           // only relevant when isLast=true
  onSaveAsNote: (content: string) => void;
}
```

**The key insight — conditional prop passing in the map:**

```tsx
messages.map((m, i) => {
  const last = i === messages.length - 1;
  return (
    <MessageBubble
      key={i}
      role={m.role}
      content={m.content}
      isLast={last}
      thinkingLabel={last ? thinkingLabel : ""}
      waitingForFirst={last ? waitingForFirst : false}
      sending={last ? sending : false}
      onSaveAsNote={saveAsNote}
    />
  );
})
```

When `thinkingLabel` or `waitingForFirst` change during streaming, non-last bubbles receive `""` / `false` both before and after — so `memo` sees no prop change and skips them. Result: **O(1) renders per token** instead of O(n).

### Stabilize `saveAsNote` with `useCallback`

`saveAsNote` is currently a plain function recreated on every render. Since it's passed as a prop to every `MessageBubble`, a new reference would break `memo` for all of them. Wrap it:

```tsx
const saveAsNote = useCallback(async (content: string) => {
  // ... same body
}, [currentPage]);
```

Dependency is `[currentPage]` because the catch fallback uses it for the note title. The reference updates only when the user navigates to a new page — stable during the entire duration of a streaming response.

### Memoize `TypingIndicator`

`TypingIndicator` takes no props. Wrap with `memo` — trivial and prevents any reconciliation cost when its parent re-renders.

---

## What `memo` Does Here

`React.memo` performs a **shallow equality check** on all props. For a completed non-last message:

| Prop | Before token | After token | Equal? |
|---|---|---|---|
| `role` | `"assistant"` | `"assistant"` | ✓ |
| `content` | `"Ownership means…"` | `"Ownership means…"` | ✓ |
| `isLast` | `false` | `false` | ✓ |
| `thinkingLabel` | `""` | `""` | ✓ (conditionally passed) |
| `waitingForFirst` | `false` | `false` | ✓ (conditionally passed) |
| `sending` | `false` | `false` | ✓ (conditionally passed) |
| `onSaveAsNote` | fn ref | fn ref | ✓ (useCallback stable) |

All equal → React skips the component entirely. No `ReactMarkdown` re-parse.

---

## Edge Cases

| Scenario | Behaviour |
|---|---|
| New user message appended | Previous last bubble re-renders once (`isLast` flips to `false`). Acceptable — one render, not per-token. |
| Empty assistant placeholder added at stream start | Previous last (user) bubble re-renders once. Same as above. |
| `sending` goes `false` after stream ends | Only last bubble re-renders to show "Save as note" button. |
| Session resume | Full array replace, all bubbles render once. No regression vs today. |
| Page navigation while dialog open | `saveAsNote` ref invalidates, picks up new `currentPage`. Correct. |

---

## Changes

| Location | Change |
|---|---|
| Line 5 | Add `memo` to React import |
| Line 71 — `TypingIndicator` | Wrap in `memo` |
| Before `BookPage` | Add `MessageBubbleProps` interface + `MessageBubble` memo component |
| Line 395 — `saveAsNote` | Wrap in `useCallback([currentPage])` |
| Line 567 — message map | Replace inline JSX with `<MessageBubble ... />` with conditional props |

All changes are self-contained within `page.tsx`. No new files required.

---

## Verification

1. `npm run build` — no TypeScript errors
2. Stream a response in the UI — no visible flicker on previous messages
3. React DevTools Profiler — only one `MessageBubble` shows as re-rendered per token; all others grayed out
4. Click "Save as note" on a non-last message — dialog opens with correct content
5. Navigate to a different PDF page, then save a note — note saves with the updated page number
6. Resume a session — all loaded messages render correctly
